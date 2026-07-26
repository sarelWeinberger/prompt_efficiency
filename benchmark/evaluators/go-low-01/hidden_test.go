package stats

import "testing"

func TestAverageHiddenMixed(t *testing.T) {
	if got := Average([]int{1, 2, 3, 4}); got != 2.5 {
		t.Fatalf("got %v want 2.5", got)
	}
}

func TestAverageHiddenNegative(t *testing.T) {
	if got := Average([]int{-3, 2}); got != -0.5 {
		t.Fatalf("got %v want -0.5", got)
	}
}
