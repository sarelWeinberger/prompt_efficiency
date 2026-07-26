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
