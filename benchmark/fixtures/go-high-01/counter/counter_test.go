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
