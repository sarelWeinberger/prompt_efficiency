package textutil

import "testing"

func TestNormalizeHiddenTabsNewlines(t *testing.T) {
	if got := Normalize(" a\t\n b \t"); got != "a b" {
		t.Fatalf("got %q want %q", got, "a b")
	}
}

func TestNormalizeHiddenEmpty(t *testing.T) {
	if got := Normalize("   "); got != "" {
		t.Fatalf("got %q want empty", got)
	}
}
