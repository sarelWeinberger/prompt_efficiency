package textutil

import "strings"

// Normalize trims the string and collapses internal whitespace runs to
// single spaces.
func Normalize(s string) string {
	return strings.TrimSpace(s)
}
