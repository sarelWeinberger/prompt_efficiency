package config

import "testing"

func TestEnvWinsOverFile(t *testing.T) {
	got := Load(
		map[string]string{"PORT": "3000"},
		map[string]string{"PORT": "8080"},
		[]string{"PORT=9090"},
	)
	if got["PORT"] != "9090" {
		t.Fatalf("PORT = %q, want 9090", got["PORT"])
	}
}

func TestFileWinsOverDefault(t *testing.T) {
	got := Load(
		map[string]string{"HOST": "localhost"},
		map[string]string{"HOST": "example.com"},
		nil,
	)
	if got["HOST"] != "example.com" {
		t.Fatalf("HOST = %q, want example.com", got["HOST"])
	}
}
