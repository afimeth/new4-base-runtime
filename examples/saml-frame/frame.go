package main

import (
	"bytes"
	"compress/flate"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"net/url"
	"regexp"
	"strings"
	"time"
)

const (
	frameSchema     = "new4.identity.saml-frame/1"
	protocolSAML20  = "SAML-2.0"
	noAuthority     = "NONE_UNVERIFIED_DEMO"
	nameIDTransient = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
	bindingHTTPPost = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
	samlProtocolNS  = "urn:oasis:names:tc:SAML:2.0:protocol"
	samlAssertionNS = "urn:oasis:names:tc:SAML:2.0:assertion"
)

var requestIDPattern = regexp.MustCompile(`^_[0-9a-f]{32}$`)

type frameSP struct {
	EntityID string `json:"entity_id"`
	ACSURL   string `json:"acs_url"`
}

type frameIdP struct {
	SSOURL string `json:"sso_url"`
}

// Frame describes a non-authoritative, illustrative service-provider request.
// This package has NO SAML response consumer or trust/identity mapping.
type Frame struct {
	Schema       string   `json:"schema"`
	Protocol     string   `json:"protocol"`
	NameIDFormat string   `json:"name_id_format"`
	Authority    string   `json:"authority"`
	SP           frameSP  `json:"sp"`
	IdP          frameIdP `json:"idp"`
}

func loadFrame(data []byte) (Frame, error) {
	var f Frame
	if len(data) > 8192 {
		return f, errors.New("FRAME_SIZE_LIMIT")
	}
	d := json.NewDecoder(bytes.NewReader(data))
	d.DisallowUnknownFields()
	if err := d.Decode(&f); err != nil {
		return f, fmt.Errorf("INVALID_FRAME_JSON: %w", err)
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return f, errors.New("TRAILING_FRAME_DATA")
	}
	return f, f.validate()
}

func (f Frame) validate() error {
	if f.Schema != frameSchema || f.Protocol != protocolSAML20 || f.NameIDFormat != nameIDTransient || f.Authority != noAuthority {
		return errors.New("FRAME_CONTRACT_MISMATCH")
	}
	for _, endpoint := range []string{f.SP.EntityID, f.SP.ACSURL, f.IdP.SSOURL} {
		if err := requireExampleHTTPS(endpoint); err != nil {
			return err
		}
	}
	return nil
}

func requireExampleHTTPS(raw string) error {
	u, err := url.Parse(raw)
	if err != nil || u.Scheme != "https" || u.Host == "" || u.User != nil || u.Fragment != "" || u.RawQuery != "" || u.Opaque != "" || strings.TrimSpace(raw) != raw || strings.ContainsAny(raw, "\r\n\t") {
		return errors.New("INVALID_DEMO_HTTPS_ENDPOINT")
	}
	return nil
}

// newRequestID uses 128 bits of randomness. Reusing IDs must be prevented by
// a real SP's pending-request store, which is deliberately absent here.
func newRequestID(random io.Reader) (string, error) {
	var b [16]byte
	if _, err := io.ReadFull(random, b[:]); err != nil {
		return "", fmt.Errorf("REQUEST_ID_ENTROPY_UNAVAILABLE: %w", err)
	}
	return "_" + hex.EncodeToString(b[:]), nil
}

type authnRequest struct {
	XMLName      xml.Name     `xml:"urn:oasis:names:tc:SAML:2.0:protocol AuthnRequest"`
	ID           string       `xml:"ID,attr"`
	Version      string       `xml:"Version,attr"`
	IssueInstant string       `xml:"IssueInstant,attr"`
	Destination  string       `xml:"Destination,attr"`
	ACSURL       string       `xml:"AssertionConsumerServiceURL,attr"`
	Binding      string       `xml:"ProtocolBinding,attr"`
	Issuer       samlIssuer   `xml:"urn:oasis:names:tc:SAML:2.0:assertion Issuer"`
	NameID       nameIDPolicy `xml:"urn:oasis:names:tc:SAML:2.0:protocol NameIDPolicy"`
}

type samlIssuer struct {
	Value string `xml:",chardata"`
}

type nameIDPolicy struct {
	Format      string `xml:"Format,attr"`
	AllowCreate bool   `xml:"AllowCreate,attr"`
}

func buildAuthnRequest(f Frame, id string, at time.Time) ([]byte, error) {
	if err := f.validate(); err != nil {
		return nil, err
	}
	if !requestIDPattern.MatchString(id) || at.IsZero() {
		return nil, errors.New("INVALID_REQUEST_ID_OR_TIME")
	}
	message := authnRequest{
		ID: id, Version: "2.0", IssueInstant: at.UTC().Format(time.RFC3339),
		Destination: f.IdP.SSOURL, ACSURL: f.SP.ACSURL, Binding: bindingHTTPPost,
		Issuer: samlIssuer{Value: f.SP.EntityID},
		NameID: nameIDPolicy{Format: f.NameIDFormat, AllowCreate: true},
	}
	b, err := xml.MarshalIndent(message, "", "  ")
	if err != nil {
		return nil, err
	}
	return append([]byte(xml.Header), append(b, '\n')...), nil
}

// redirectURL shows the HTTP-Redirect message encoding (raw DEFLATE, base64,
// URL encoding). It does NOT sign the query parameters. Never use this URL
// for actual identity/authentication or rely on any SAML response from it.
func redirectURL(idpSSOURL string, requestXML []byte) (string, error) {
	if err := requireExampleHTTPS(idpSSOURL); err != nil {
		return "", err
	}
	if len(requestXML) == 0 || len(requestXML) > 16384 {
		return "", errors.New("REQUEST_XML_SIZE_LIMIT")
	}
	var compressed bytes.Buffer
	w, err := flate.NewWriter(&compressed, flate.DefaultCompression)
	if err != nil {
		return "", err
	}
	if _, err := w.Write(requestXML); err != nil {
		return "", err
	}
	if err := w.Close(); err != nil {
		return "", err
	}
	u, _ := url.Parse(idpSSOURL)
	query := u.Query()
	query.Set("SAMLRequest", base64.StdEncoding.EncodeToString(compressed.Bytes()))
	u.RawQuery = query.Encode()
	return u.String(), nil
}
