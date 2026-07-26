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
