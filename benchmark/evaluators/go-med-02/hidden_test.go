package client

import (
	"bytes"
	"testing"
)

func TestLimitLargerThanContent(t *testing.T) {
	c := &StubClient{Content: map[string][]byte{"u": []byte("ab")}}
	got, err := c.FetchWithLimit("u", 10)
	if err != nil || !bytes.Equal(got, []byte("ab")) {
		t.Fatalf("got %q %v", got, err)
	}
}

func TestZeroLimit(t *testing.T) {
	c := &StubClient{Content: map[string][]byte{"u": []byte("ab")}}
	got, err := c.FetchWithLimit("u", 0)
	if err != nil || len(got) != 0 {
		t.Fatalf("got %q %v, want empty", got, err)
	}
}

func TestFetcherInterfaceStillSatisfied(t *testing.T) {
	var f Fetcher = &StubClient{}
	_ = f
}
