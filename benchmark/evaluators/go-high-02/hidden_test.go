package config

import "testing"

func TestEnvOnlyKey(t *testing.T) {
	got := Load(nil, nil, []string{"NEW=1"})
	if got["NEW"] != "1" {
		t.Fatalf("NEW = %q, want 1", got["NEW"])
	}
}

func TestDefaultSurvives(t *testing.T) {
	got := Load(map[string]string{"A": "d"}, nil, nil)
	if got["A"] != "d" {
		t.Fatalf("A = %q, want d", got["A"])
	}
}

func TestEmptyEnvValueCountsAsSet(t *testing.T) {
	got := Load(map[string]string{"A": "d"}, nil, []string{"A="})
	if got["A"] != "" {
		t.Fatalf("A = %q, want empty string", got["A"])
	}
}
