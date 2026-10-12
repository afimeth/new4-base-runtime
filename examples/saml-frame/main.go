package main

import (
	"crypto/rand"
	"embed"
	"fmt"
	"os"
	"time"
)

//go:embed frame.json
var embeddedFrame embed.FS

func main() {
	data, err := embeddedFrame.ReadFile("frame.json")
	if err != nil {
		fail(err)
	}
	frame, err := loadFrame(data)
	if err != nil {
		fail(err)
	}
	id, err := newRequestID(rand.Reader)
	if err != nil {
		fail(err)
	}
	message, err := buildAuthnRequest(frame, id, time.Now().UTC())
	if err != nil {
		fail(err)
	}
	link, err := redirectURL(frame.IdP.SSOURL, message)
	if err != nil {
		fail(err)
	}
	fmt.Println("SAML 2.0 SP-initiated AuthnRequest FRAME ONLY — UNSIGNED / NOT FOR LOGIN")
	fmt.Print(string(message))
	fmt.Println("Illustrative HTTP-Redirect URL (do not visit/use for SSO):", link)
	fmt.Println("AUTHORITY=NONE_UNVERIFIED_DEMO; RESPONSE_CONSUMER=NOT_IMPLEMENTED; OWNERAUTH=DENIED")
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
