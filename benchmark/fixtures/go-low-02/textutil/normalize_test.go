package textutil

import "testing"

func TestNormalizeCollapse(t *testing.T) {
	if got := Normalize("a  b"); got != "a b" {
		t.Fatalf("got %q want %q", got, "a b")
	}
}

func TestNormalizeTrim(t *testing.T) {
	if got := Normalize("  hi  "); got != "hi" {
		t.Fatalf("got %q want %q", got, "hi")
	}
}
