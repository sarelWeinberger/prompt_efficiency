package inventory

import "testing"

func TestReserveExact(t *testing.T) {
	s := NewStore()
	s.Add("a", 4)
	if err := Reserve(s, "a", 4); err != nil {
		t.Fatal(err)
	}
	if got := s.Available("a"); got != 0 {
		t.Fatalf("got %d want 0", got)
	}
}

func TestOverReserveLeavesState(t *testing.T) {
	s := NewStore()
	s.Add("a", 2)
	_ = Reserve(s, "a", 5)
	if got := s.Available("a"); got != 2 {
		t.Fatalf("state changed: got %d want 2", got)
	}
}

func TestTwoSkusIndependent(t *testing.T) {
	s := NewStore()
	s.Add("a", 3)
	s.Add("b", 1)
	if err := Reserve(s, "a", 2); err != nil {
		t.Fatal(err)
	}
	if s.Available("b") != 1 {
		t.Fatal("sku b affected")
	}
}
