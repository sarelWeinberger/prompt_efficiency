package client

import (
	"bytes"
	"testing"
)

func TestFetchUnchanged(t *testing.T) {
	c := &StubClient{Content: map[string][]byte{"u": []byte("payload")}}
	got, err := c.Fetch("u")
	if err != nil || !bytes.Equal(got, []byte("payload")) {
		t.Fatalf("Fetch broken: %q %v", got, err)
	}
}

func TestFetchWithLimitTruncates(t *testing.T) {
	c := &StubClient{Content: map[string][]byte{"u": []byte("payload")}}
	var lf LimitedFetcher = c
	got, err := lf.FetchWithLimit("u", 3)
	if err != nil || string(got) != "pay" {
		t.Fatalf("FetchWithLimit = %q, %v; want \"pay\"", got, err)
	}
}
