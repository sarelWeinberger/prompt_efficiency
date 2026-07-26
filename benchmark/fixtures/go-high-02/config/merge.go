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
