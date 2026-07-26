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
