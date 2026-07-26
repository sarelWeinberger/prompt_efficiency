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
