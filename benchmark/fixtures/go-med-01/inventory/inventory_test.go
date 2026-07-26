package inventory

import "testing"

func TestReserveDeducts(t *testing.T) {
	s := NewStore()
	s.Add("widget", 5)
	if err := Reserve(s, "widget", 3); err != nil {
		t.Fatal(err)
	}
	if got := s.Available("widget"); got != 2 {
		t.Fatalf("Available = %d, want 2", got)
	}
}

func TestOverReserveErrors(t *testing.T) {
	s := NewStore()
	s.Add("widget", 2)
	if err := Reserve(s, "widget", 3); err == nil {
		t.Fatal("expected error")
	}
}
