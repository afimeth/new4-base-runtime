package main

import (
	"bytes"
	"compress/flate"
	"crypto/rand"
	"encoding/base64"
	"encoding/xml"
	"io"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"
)

const testRequestID = "_0123456789abcdef0123456789abcdef"

var fixtureTime = time.Date(2026, 10, 12, 9, 0, 0, 0, time.UTC)

func getFixtureFrame(t *testing.T) Frame {
	t.Helper()
	b, err := os.ReadFile("frame.json")
	if err != nil {
		t.Fatal(err)
	}
	frame, err := loadFrame(b)
	if err != nil {
		t.Fatal(err)
	}
	return frame
}

func TestFrameAndAuthnRequest(t *testing.T) {
	frame := getFixtureFrame(t)
	b, err := buildAuthnRequest(frame, testRequestID, fixtureTime)
	if err != nil {
		t.Fatal(err)
	}
	var message authnRequest
	if err := xml.Unmarshal(b, &message); err != nil {
		t.Fatal(err)
	}
	if message.XMLName.Space != samlProtocolNS || message.XMLName.Local != "AuthnRequest" || message.Version != "2.0" || message.IssueInstant != "2026-10-12T09:00:00Z" || message.ID != testRequestID {
		t.Fatalf("unexpected SAML request: %+v", message)
	}
	if message.Issuer.Value != frame.SP.EntityID || message.Destination != frame.IdP.SSOURL || message.ACSURL != frame.SP.ACSURL || message.NameID.Format != nameIDTransient || !message.NameID.AllowCreate || message.Binding != bindingHTTPPost {
		t.Fatalf("SAML attributes mismatch: %+v", message)
	}
	if bytes.Contains(b, []byte("<Assertion")) || bytes.Contains(b, []byte("<Response")) || bytes.Contains(b, []byte("Signature")) {
		t.Fatal("demo must not claim to sign or provide assertions")
	}
	expected, err := os.ReadFile("authn-request.xml")
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(b, expected) {
		t.Fatalf("fixture drift:\n%s\nexpected:\n%s", b, expected)
	}
}

func TestHTTPRedirectDeflateRoundTrip(t *testing.T) {
	frame := getFixtureFrame(t)
	b, err := buildAuthnRequest(frame, testRequestID, fixtureTime)
	if err != nil {
		t.Fatal(err)
	}
	link, err := redirectURL(frame.IdP.SSOURL, b)
	if err != nil {
		t.Fatal(err)
	}
	u, err := url.Parse(link)
	if err != nil {
		t.Fatal(err)
	}
	if u.Scheme != "https" || u.Host != "idp.example.invalid" || u.Query().Has("Signature") || u.Query().Has("SigAlg") {
		t.Fatal("unexpected redirect")
	}
	deflated, err := base64.StdEncoding.DecodeString(u.Query().Get("SAMLRequest"))
	if err != nil {
		t.Fatal(err)
	}
	r := flate.NewReader(bytes.NewReader(deflated))
	defer r.Close()
	decoded, err := io.ReadAll(io.LimitReader(r, 16385))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(decoded, b) {
		t.Fatal("redirect round-trip changed request")
	}
}

func TestFailClosedFrameValidation(t *testing.T) {
	f := getFixtureFrame(t)
	tests := []struct {
		name string
		edit func(*Frame)
	}{
		{"authority_override", func(f *Frame) { f.Authority = "ownerauth" }},
		{"bad_schema", func(f *Frame) { f.Schema = "unknown" }},
		{"http_acs", func(f *Frame) { f.SP.ACSURL = "http://sp.example.invalid/acs" }},
		{"user_info", func(f *Frame) { f.IdP.SSOURL = "https://user:secret@idp.example.invalid/sso" }},
		{"fragment", func(f *Frame) { f.IdP.SSOURL += "#fragment" }},
		{"query", func(f *Frame) { f.IdP.SSOURL += "?x=1" }},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			modified := f
			tt.edit(&modified)
			if err := modified.validate(); err == nil {
				t.Fatal("must reject invalid frame")
			}
		})
	}
	for _, bad := range []string{`{"schema":"other"}`, `{"schema":"x","unknown_field":true}`, string(bytes.Repeat([]byte("x"), 8193))} {
		if _, err := loadFrame([]byte(bad)); err == nil {
			t.Fatal("must reject invalid or oversized JSON")
		}
	}
	b, _ := os.ReadFile("frame.json")
	if _, err := loadFrame(append(b, []byte("{}")...)); err == nil {
		t.Fatal("must reject trailing JSON")
	}
}

func TestRequestIDAndTimeRejectInvalid(t *testing.T) {
	f := getFixtureFrame(t)
	for _, id := range []string{"", "_abc", "unsafe\"ID", "_0123456789abcdef0123456789abcdef-2"} {
		if _, err := buildAuthnRequest(f, id, fixtureTime); err == nil {
			t.Fatal("invalid ID accepted")
		}
	}
	if _, err := buildAuthnRequest(f, testRequestID, time.Time{}); err == nil {
		t.Fatal("zero time accepted")
	}
	if _, err := newRequestID(strings.NewReader("short")); err == nil {
		t.Fatal("must fail on missing entropy")
	}
	first, err := newRequestID(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	second, err := newRequestID(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	if first == second || !requestIDPattern.MatchString(first) || !requestIDPattern.MatchString(second) {
		t.Fatal("invalid/non-unique random IDs")
	}
}

func TestXMLEscaping(t *testing.T) {
	f := getFixtureFrame(t)
	f.SP.EntityID = "https://sp.example.invalid/new4&other"
	b, err := buildAuthnRequest(f, testRequestID, fixtureTime)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(b, []byte("&amp;")) {
		t.Fatalf("missing XML escape: %s", b)
	}
	var parsed authnRequest
	if err := xml.Unmarshal(b, &parsed); err != nil {
		t.Fatal(err)
	}
	if parsed.Issuer.Value != f.SP.EntityID {
		t.Fatal("issuer changed in XML round trip")
	}
}

func TestSPMetadataFixtureConsistency(t *testing.T) {
	frame := getFixtureFrame(t)
	data, err := os.ReadFile("sp-metadata.xml")
	if err != nil {
		t.Fatal(err)
	}
	var metadata struct {
		XMLName  xml.Name `xml:"urn:oasis:names:tc:SAML:2.0:metadata EntityDescriptor"`
		EntityID string   `xml:"entityID,attr"`
		SP       struct {
			XMLName          xml.Name `xml:"urn:oasis:names:tc:SAML:2.0:metadata SPSSODescriptor"`
			SignedRequests   string   `xml:"AuthnRequestsSigned,attr"`
			SignedAssertions string   `xml:"WantAssertionsSigned,attr"`
			ACS              struct {
				Binding  string `xml:"Binding,attr"`
				Location string `xml:"Location,attr"`
			} `xml:"urn:oasis:names:tc:SAML:2.0:metadata AssertionConsumerService"`
		} `xml:"urn:oasis:names:tc:SAML:2.0:metadata SPSSODescriptor"`
	}
	if err := xml.Unmarshal(data, &metadata); err != nil {
		t.Fatal(err)
	}
	if metadata.EntityID != frame.SP.EntityID || metadata.SP.SignedRequests != "false" || metadata.SP.SignedAssertions != "true" || metadata.SP.ACS.Binding != bindingHTTPPost || metadata.SP.ACS.Location != frame.SP.ACSURL {
		t.Fatalf("metadata fixture mismatch: %+v", metadata)
	}
}

func TestRedirectRejectsInvalidInputs(t *testing.T) {
	for _, raw := range []string{"http://idp.example.invalid/sso", "https://user:pass@idp.example.invalid/sso", "https://idp.example.invalid/sso?Signature=x"} {
		if _, err := redirectURL(raw, []byte("test")); err == nil {
			t.Fatalf("accepted invalid target: %s", raw)
		}
	}
	for _, request := range [][]byte{nil, bytes.Repeat([]byte("x"), 16385)} {
		if _, err := redirectURL("https://idp.example.invalid/sso", request); err == nil {
			t.Fatal("accepted empty or oversized request")
		}
	}
}
