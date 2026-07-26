#!/usr/bin/env python3
"""Materialize the 6 Go benchmark tasks (std library only, one module per fixture)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
TASKS = ROOT / "tasks"
EVAL = ROOT / "evaluators"

T = {}

# ---------------------------------------------------------------- go-low-01
T["go-low-01"] = dict(
    meta=dict(
        language="go", complexity="low", split="dev", pilot=True,
        objective="Fix the arithmetic bug in stats/stats.go: Average must return the "
                  "true mean as a float64 (currently integer division truncates it).",
        objective_vague="statistics helpers",
        misleading_hint="the empty-slice guard",
        scope="stats/stats.go only",
        allowed_paths=["stats/stats.go"],
        criteria="Average([]int{1, 2}) == 1.5; empty slice still returns 0; "
                 "go test ./... passes",
        test_cmd="go test ./...",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "go.mod": "module bench/golow01\n\ngo 1.24\n",
        "stats/stats.go": '''\
package stats

// Average returns the arithmetic mean of xs, or 0 for an empty slice.
func Average(xs []int) float64 {
	if len(xs) == 0 {
		return 0
	}
	sum := 0
	for _, x := range xs {
		sum += x
	}
	return float64(sum / len(xs))
}
''',
        "stats/stats_test.go": '''\
package stats

import "testing"

func TestAverageFraction(t *testing.T) {
	if got := Average([]int{1, 2}); got != 1.5 {
		t.Fatalf("Average([1 2]) = %v, want 1.5", got)
	}
}

func TestAverageEmpty(t *testing.T) {
	if got := Average(nil); got != 0 {
		t.Fatalf("Average(nil) = %v, want 0", got)
	}
}
''',
    },
    hidden={
        "hidden_test.go": dict(dst="stats/hidden_test.go", content='''\
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
'''),
    },
)

# ---------------------------------------------------------------- go-low-02 (holdout)
T["go-low-02"] = dict(
    meta=dict(
        language="go", complexity="low", split="holdout", pilot=False,
        objective="Repair the failing unit test by fixing the code (the test is "
                  "correct): Normalize in textutil/normalize.go must trim the string "
                  "AND collapse internal whitespace runs (spaces, tabs, newlines) into "
                  "single spaces.",
        objective_vague="text normalization",
        misleading_hint="the test's expected constants",
        scope="textutil/normalize.go only",
        allowed_paths=["textutil/normalize.go"],
        criteria='Normalize("  a\\t\\tb  ") == "a b"; go test ./... passes',
        test_cmd="go test ./...",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "go.mod": "module bench/golow02\n\ngo 1.24\n",
        "textutil/normalize.go": '''\
package textutil

import "strings"

// Normalize trims the string and collapses internal whitespace runs to
// single spaces.
func Normalize(s string) string {
	return strings.TrimSpace(s)
}
''',
        "textutil/normalize_test.go": '''\
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
''',
    },
    hidden={
        "hidden_test.go": dict(dst="textutil/hidden_test.go", content='''\
package textutil

import "testing"

func TestNormalizeHiddenTabsNewlines(t *testing.T) {
	if got := Normalize(" a\\t\\n b \\t"); got != "a b" {
		t.Fatalf("got %q want %q", got, "a b")
	}
}

func TestNormalizeHiddenEmpty(t *testing.T) {
	if got := Normalize("   "); got != "" {
		t.Fatalf("got %q want empty", got)
	}
}
'''),
    },
)

# ---------------------------------------------------------------- go-med-01
T["go-med-01"] = dict(
    meta=dict(
        language="go", complexity="medium", split="dev", pilot=False,
        objective="Fix the reservation bug spanning inventory/store.go and "
                  "inventory/reserve.go: Reserve must actually deduct the reserved "
                  "quantity from availability, and reserving more than is available "
                  "must return an error without changing state.",
        objective_vague="stock levels",
        misleading_hint="map initialization in NewStore",
        scope="the inventory package (inventory/)",
        allowed_paths=["inventory/store.go", "inventory/reserve.go"],
        criteria="after Add(sku,5); Reserve(sku,3) => Available(sku)==2; over-reserve "
                 "errors and leaves state unchanged; go test ./... passes",
        test_cmd="go test ./...",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "go.mod": "module bench/gomed01\n\ngo 1.24\n",
        "inventory/store.go": '''\
package inventory

// Store tracks on-hand quantity per SKU.
type Store struct {
	items map[string]int
}

func NewStore() *Store {
	return &Store{items: map[string]int{}}
}

func (s *Store) Add(sku string, n int) {
	s.items[sku] += n
}

func (s *Store) Available(sku string) int {
	return s.items[sku]
}
''',
        "inventory/reserve.go": '''\
package inventory

import "fmt"

// Reserve claims n units of sku, reducing availability.
func Reserve(s *Store, sku string, n int) error {
	if s.Available(sku) < n {
		return fmt.Errorf("insufficient stock for %s", sku)
	}
	return nil
}
''',
        "inventory/inventory_test.go": '''\
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
''',
    },
    hidden={
        "hidden_test.go": dict(dst="inventory/hidden_test.go", content='''\
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
'''),
    },
)

# ---------------------------------------------------------------- go-med-02 (holdout)
T["go-med-02"] = dict(
    meta=dict(
        language="go", complexity="medium", split="holdout", pilot=False,
        objective="Implement a backward-compatible interface change in client/: add a "
                  "LimitedFetcher interface with FetchWithLimit(url string, limit int) "
                  "([]byte, error) returning at most limit bytes, implement it on "
                  "StubClient, and keep the existing Fetcher interface and Fetch "
                  "behavior completely unchanged.",
        objective_vague="the fetch client API",
        misleading_hint="changing the existing Fetcher interface in place",
        scope="the client package (client/)",
        allowed_paths=["client/client.go", "client/limited.go"],
        criteria="existing Fetch tests untouched and passing; FetchWithLimit truncates "
                 "to limit; go test ./... passes",
        test_cmd="go test ./...",
        stop="Stop when the tests pass.",
        expected_scope_files=2,
    ),
    fixture={
        "go.mod": "module bench/gomed02\n\ngo 1.24\n",
        "client/client.go": '''\
package client

// Fetcher is the stable, published interface. Do not break it.
type Fetcher interface {
	Fetch(url string) ([]byte, error)
}

// StubClient returns canned content for tests and local development.
type StubClient struct {
	Content map[string][]byte
}

func (c *StubClient) Fetch(url string) ([]byte, error) {
	return c.Content[url], nil
}
''',
        "client/client_test.go": '''\
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
		t.Fatalf("FetchWithLimit = %q, %v; want \\"pay\\"", got, err)
	}
}
''',
    },
    hidden={
        "hidden_test.go": dict(dst="client/hidden_test.go", content='''\
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
'''),
    },
)

# ---------------------------------------------------------------- go-high-01
T["go-high-01"] = dict(
    meta=dict(
        language="go", complexity="high", split="dev", pilot=True,
        objective="Fix the concurrency bug in counter/counter.go: Inc and Get are "
                  "called from many goroutines and currently corrupt state (or crash "
                  "with concurrent map writes). Make Counter safe for concurrent use "
                  "while keeping its API unchanged.",
        objective_vague="metrics counting",
        misleading_hint="the test's goroutine count",
        scope="counter/counter.go only",
        allowed_paths=["counter/counter.go"],
        criteria="50 goroutines x 100 Inc yield exactly 5000 and no crash; "
                 "go test ./... passes",
        test_cmd="go test ./...",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "go.mod": "module bench/gohigh01\n\ngo 1.24\n",
        "counter/counter.go": '''\
package counter

// Counter tallies named events. It is used from many goroutines.
type Counter struct {
	counts map[string]int
}

func New() *Counter {
	return &Counter{counts: map[string]int{}}
}

func (c *Counter) Inc(key string) {
	c.counts[key]++
}

func (c *Counter) Get(key string) int {
	return c.counts[key]
}
''',
        "counter/counter_test.go": '''\
package counter

import (
	"sync"
	"testing"
)

func TestConcurrentInc(t *testing.T) {
	c := New()
	var wg sync.WaitGroup
	for g := 0; g < 50; g++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < 100; i++ {
				c.Inc("hits")
			}
		}()
	}
	wg.Wait()
	if got := c.Get("hits"); got != 5000 {
		t.Fatalf("Get(hits) = %d, want 5000", got)
	}
}
''',
    },
    hidden={
        "hidden_test.go": dict(dst="counter/hidden_test.go", content='''\
package counter

import (
	"sync"
	"testing"
)

func TestConcurrentMultiKey(t *testing.T) {
	c := New()
	var wg sync.WaitGroup
	keys := []string{"a", "b", "c", "d"}
	for g := 0; g < 40; g++ {
		wg.Add(1)
		go func(g int) {
			defer wg.Done()
			for i := 0; i < 50; i++ {
				c.Inc(keys[g%len(keys)])
			}
		}(g)
	}
	wg.Wait()
	total := 0
	for _, k := range keys {
		total += c.Get(k)
	}
	if total != 2000 {
		t.Fatalf("total = %d, want 2000", total)
	}
}
'''),
    },
)

# ---------------------------------------------------------------- go-high-02 (holdout)
T["go-high-02"] = dict(
    meta=dict(
        language="go", complexity="high", split="holdout", pilot=False,
        objective="Configuration precedence is broken: values set via environment "
                  "variables are supposed to override file values, which override "
                  "defaults (env > file > defaults), but env values are being lost. "
                  "Find the real root cause across the config package and fix it.",
        objective_vague="configuration precedence",
        misleading_hint="the ApplyEnv ordering in load.go",
        scope="the config package (config/)",
        allowed_paths=["config/load.go", "config/merge.go"],
        criteria="env value wins over file value; file wins over default; "
                 "go test ./... passes",
        test_cmd="go test ./...",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "go.mod": "module bench/gohigh02\n\ngo 1.24\n",
        "config/merge.go": '''\
package config

// Merge overlays src onto dst: keys present in src replace keys in dst.
func Merge(dst, src map[string]string) map[string]string {
	out := map[string]string{}
	for k, v := range src {
		out[k] = v
	}
	for k, v := range dst {
		out[k] = v
	}
	return out
}
''',
        "config/load.go": '''\
package config

import "strings"

// Load builds the effective config. Precedence: env > file > defaults.
// ApplyEnv runs last, so environment values always win.
func Load(defaults, fileVals map[string]string, environ []string) map[string]string {
	cfg := Merge(defaults, fileVals)
	cfg = ApplyEnv(cfg, environ)
	return cfg
}

// ApplyEnv overlays KEY=VALUE pairs from environ onto cfg.
func ApplyEnv(cfg map[string]string, environ []string) map[string]string {
	envVals := map[string]string{}
	for _, kv := range environ {
		parts := strings.SplitN(kv, "=", 2)
		if len(parts) == 2 {
			envVals[parts[0]] = parts[1]
		}
	}
	return Merge(cfg, envVals)
}
''',
        "config/config_test.go": '''\
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
''',
    },
    hidden={
        "hidden_test.go": dict(dst="config/hidden_test.go", content='''\
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
'''),
    },
)


def write_all():
    for tid, spec in T.items():
        fixdir = FIX / tid
        for rel, content in spec["fixture"].items():
            p = fixdir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        evdir = EVAL / tid
        evdir.mkdir(parents=True, exist_ok=True)
        copies = []
        for name, h in spec["hidden"].items():
            (evdir / name).write_text(h["content"])
            copies.append({"src": name, "dst": h["dst"]})
        (evdir / "eval.yaml").write_text(json.dumps({
            "hidden_copy": copies,
            "hidden_cmd": "go test ./...",
            "hidden_cleanup": [c["dst"] for c in copies],
        }, indent=1))
        meta = dict(spec["meta"])
        meta["id"] = tid
        TASKS.mkdir(parents=True, exist_ok=True)
        (TASKS / f"{tid}.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {len(T)} go tasks")


if __name__ == "__main__":
    write_all()
