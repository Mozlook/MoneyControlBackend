package jwtverifier

import (
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"

	"github.com/Mozlook/MoneyControlBackend/internal/config"
)

type KeyStore map[string]*rsa.PublicKey

func LoadKeys(defs []config.Keys) (KeyStore, error) {
	ks := make(KeyStore)
	for _, def := range defs {

		if def.Kid == "" {
			return nil, fmt.Errorf("empty kid in key def")
		}
		if def.PublicKeyPath == "" {
			return nil, fmt.Errorf("epmty PublicKeyPath for kid=%s", def.Kid)
		}

		pemBytes, err := os.ReadFile(def.PublicKeyPath)
		if err != nil {
			return nil, fmt.Errorf("read key (%s): %w", def.PublicKeyPath, err)
		}

		block, _ := pem.Decode(pemBytes)
		if block == nil {
			return nil, fmt.Errorf("no PEM block ins %s", def.PublicKeyPath)
		}

		var pub *rsa.PublicKey
		switch block.Type {
		case "PUBLIC KEY":
			// PKIX (SubjectPublicKeyInfo)
			parsed, err := x509.ParsePKIXPublicKey(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parse PKIX public key (%s): %w", def.PublicKeyPath, err)
			}
			var ok bool
			pub, ok = parsed.(*rsa.PublicKey)
			if !ok {
				return nil, fmt.Errorf("public key in %s is not RSA", def.PublicKeyPath)
			}
		case "RSA PUBLIC KEY":
			// PKCS#1 (RSAPublicKey)
			var err error
			pub, err = x509.ParsePKCS1PublicKey(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parse PKCS1 public key (%s): %w", def.PublicKeyPath, err)
			}
		default:
			return nil, fmt.Errorf("unsupported PEM type %q in %s", block.Type, def.PublicKeyPath)

		}
		ks[def.Kid] = pub
	}
	if len(ks) == 0 {
		return nil, fmt.Errorf("no keys loaded")
	}

	return ks, nil
}
