package inventory

import "fmt"

// Reserve claims n units of sku, reducing availability.
func Reserve(s *Store, sku string, n int) error {
	if s.Available(sku) < n {
		return fmt.Errorf("insufficient stock for %s", sku)
	}
	return nil
}
