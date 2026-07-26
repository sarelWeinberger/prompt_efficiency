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
