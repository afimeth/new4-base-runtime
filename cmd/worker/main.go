// A bounded Go worker. JSON in/out; no shell, network or filesystem effects.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode"
)

type Request struct {
	Schema string          `json:"schema"`
	ID     string          `json:"id"`
	Tool   string          `json:"tool"`
	Input  json.RawMessage `json:"input"`
}
type Token struct {
	Text   string `json:"text"`
	Folded string `json:"folded"`
	Kind   string `json:"kind"`
	Start  int    `json:"start"`
	End    int    `json:"end"`
}

func tokens(text string) []Token {
	chars := []rune(text)
	result := []Token{}
	for i := 0; i < len(chars); {
		if unicode.IsSpace(chars[i]) {
			i++
			continue
		}
		start := i
		kind := "punctuation"
		if unicode.IsLetter(chars[i]) || unicode.IsNumber(chars[i]) {
			kind = "word"
			if unicode.IsNumber(chars[i]) {
				kind = "number"
			}
			i++
			for i < len(chars) && (unicode.IsLetter(chars[i]) || unicode.IsNumber(chars[i]) || unicode.IsMark(chars[i]) || chars[i] == '\'' || chars[i] == '-') {
				i++
			}
		} else {
			i++
		}
		value := string(chars[start:i])
		result = append(result, Token{value, strings.ToLower(value), kind, start, i})
	}
	return result
}

func parse(text string) (any, error) {
	if strings.TrimSpace(text) == "" || len([]rune(text)) > 2000 {
		return nil, fmt.Errorf("INVALID_UTTERANCE")
	}
	ts := tokens(text)
	keywords := []string{}
	intent := "find"
	frame := "context"
	recognized := false
	stop := map[string]bool{"a": true, "an": true, "the": true, "please": true, "can": true, "you": true, "me": true, "my": true, "for": true, "about": true, "i": true, "want": true, "to": true, "and": true, "of": true, "in": true}
	verbs := map[string]string{"find": "find", "search": "find", "show": "find", "look": "find", "summarize": "brief", "brief": "brief", "review": "review", "plan": "plan", "prepare": "plan", "draft": "draft", "create": "draft", "calculate": "calculate", "sum": "calculate", "route": "route", "path": "route"}
	for _, t := range ts {
		if t.Kind == "punctuation" {
			continue
		}
		if t.Folded == "total" && len(keywords) == 0 && !recognized {
			intent = "calculate"
			recognized = true
			continue
		}
		if v, ok := verbs[t.Folded]; ok && !recognized {
			intent = v
			recognized = true
			continue
		}
		if !stop[t.Folded] {
			keywords = append(keywords, t.Folded)
		}
	}
	if intent == "calculate" {
		frame = "math"
	}
	if intent == "route" {
		frame = "topology"
	}
	hash := sha256.Sum256([]byte(text))
	return map[string]any{"schema": "onion-parse/1", "raw_hash": hex.EncodeToString(hash[:]), "tokens": ts, "intent": intent, "frame": frame, "keywords": keywords, "intent_basis": "English verb rules; find is the explicit fallback", "semantic_confidence": nil, "layers": []string{"exact UTF-8 utterance", "Unicode word/number/punctuation spans", "English intent and frame", "source lookup or bounded computation", "reviewable proposal; no authority from text"}, "offset_unit": "Unicode code points; end exclusive; no normalization"}, nil
}

func money(text string) (any, error) {
	currency := ""
	upper := strings.ToUpper(text)
	for _, c := range []string{"USD", "EUR"} {
		if regexp.MustCompile(`\b` + c + `\b`).MatchString(upper) {
			if currency != "" {
				return nil, fmt.Errorf("MIXED_CURRENCIES")
			}
			currency = c
		}
	}
	if currency == "" {
		return nil, fmt.Errorf("CURRENCY_REQUIRED_USD_OR_EUR")
	}
	if strings.Contains(text, ",") {
		return nil, fmt.Errorf("USE_DOT_DECIMAL_NO_THOUSANDS_SEPARATOR")
	}
	if strings.Contains(text, "-") {
		return nil, fmt.Errorf("NEGATIVE_AMOUNT_UNSUPPORTED")
	}
	matches := regexp.MustCompile(`\b[0-9]+(?:\.[0-9]+)?\b`).FindAllString(text, -1)
	if len(matches) == 0 || len(matches) > 100 {
		return nil, fmt.Errorf("AMOUNT_COUNT_LIMIT")
	}
	var total int64
	amounts := []int64{}
	for _, value := range matches {
		parts := strings.Split(value, ".")
		whole, err := strconv.ParseInt(parts[0], 10, 64)
		if err != nil || whole > 1000000000 {
			return nil, fmt.Errorf("AMOUNT_LIMIT")
		}
		fraction := int64(0)
		if len(parts) == 2 {
			if len(parts[1]) > 2 {
				return nil, fmt.Errorf("MAX_TWO_DECIMAL_PLACES")
			}
			f := parts[1]
			if len(f) == 1 {
				f += "0"
			}
			fraction, _ = strconv.ParseInt(f, 10, 64)
		}
		cents := whole*100 + fraction
		total += cents
		amounts = append(amounts, cents)
	}
	return map[string]any{"currency": currency, "amounts_minor_units": amounts, "total_minor_units": total, "display": fmt.Sprintf("%s %d.%02d", currency, total/100, total%100), "method": "Exact integer minor-unit addition; no currency conversion"}, nil
}

type Graph struct {
	Nodes []string    `json:"nodes"`
	Edges [][2]string `json:"edges"`
	From  string      `json:"from"`
	To    string      `json:"to"`
}

func route(g Graph) (any, error) {
	if len(g.Nodes) > 1000 || len(g.Edges) > 4000 {
		return nil, fmt.Errorf("GRAPH_LIMIT")
	}
	nodes := map[string]bool{}
	for _, n := range g.Nodes {
		if n == "" || nodes[n] {
			return nil, fmt.Errorf("INVALID_GRAPH")
		}
		nodes[n] = true
	}
	if !nodes[g.From] || !nodes[g.To] {
		return nil, fmt.Errorf("UNKNOWN_NODE")
	}
	edges := map[string][]string{}
	for _, e := range g.Edges {
		if !nodes[e[0]] || !nodes[e[1]] {
			return nil, fmt.Errorf("DANGLING_EDGE")
		}
		edges[e[0]] = append(edges[e[0]], e[1])
	}
	for _, v := range edges {
		sort.Strings(v)
	}
	queue := []string{g.From}
	previous := map[string]string{g.From: ""}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		if cur == g.To {
			path := []string{}
			for n := cur; n != ""; n = previous[n] {
				path = append([]string{n}, path...)
			}
			return map[string]any{"path": path, "hops": len(path) - 1, "relation": "EXPLICIT_DOCUMENT_REFERENCE", "semantic_confidence": nil}, nil
		}
		for _, n := range edges[cur] {
			if _, seen := previous[n]; !seen {
				previous[n] = cur
				queue = append(queue, n)
			}
		}
	}
	return nil, fmt.Errorf("NO_RECORDED_PATH")
}

func execute(r Request) (any, error) {
	if r.Schema != "worker-request/1" || r.ID == "" || len(r.ID) > 80 {
		return nil, fmt.Errorf("INVALID_WORKER_REQUEST")
	}
	switch r.Tool {
	case "search.rank":
		var value Search
		decoder := json.NewDecoder(bytes.NewReader(r.Input))
		decoder.DisallowUnknownFields()
		if err := decoder.Decode(&value); err != nil {
			return nil, fmt.Errorf("INVALID_SEARCH_INPUT")
		}
		return rank(value)
	case "onion.parse", "math.sum":
		var value struct {
			Text string `json:"text"`
		}
		decoder := json.NewDecoder(bytes.NewReader(r.Input))
		decoder.DisallowUnknownFields()
		if err := decoder.Decode(&value); err != nil {
			return nil, fmt.Errorf("INVALID_TEXT_INPUT")
		}
		if r.Tool == "onion.parse" {
			return parse(value.Text)
		}
		if len([]rune(value.Text)) > 2000 {
			return nil, fmt.Errorf("INVALID_UTTERANCE")
		}
		return money(value.Text)
	case "graph.route":
		var value Graph
		decoder := json.NewDecoder(bytes.NewReader(r.Input))
		decoder.DisallowUnknownFields()
		if err := decoder.Decode(&value); err != nil {
			return nil, fmt.Errorf("INVALID_GRAPH_INPUT")
		}
		return route(value)
	default:
		return nil, fmt.Errorf("TOOL_NOT_ALLOWED")
	}
}

type Document struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Text  string `json:"text"`
}
type Search struct {
	Query     []string       `json:"query"`
	Documents []Document     `json:"documents"`
	Feedback  map[string]int `json:"feedback"`
}
type Ranked struct {
	ID         string   `json:"id"`
	Score      float64  `json:"score"`
	BM25       float64  `json:"bm25"`
	TitleBoost float64  `json:"title_boost"`
	Feedback   float64  `json:"feedback_adjustment"`
	Matched    []string `json:"matched_words"`
}

func words(text string) map[string]int {
	freq := map[string]int{}
	for _, token := range tokens(text) {
		if token.Kind != "punctuation" {
			freq[token.Folded]++
		}
	}
	return freq
}
func rank(input Search) (any, error) {
	if len(input.Documents) > 32 || len(input.Query) > 100 {
		return nil, fmt.Errorf("SEARCH_BUDGET")
	}
	if len(input.Documents) == 0 {
		return []Ranked{}, nil
	}
	query := map[string]bool{}
	for _, q := range input.Query {
		query[q] = true
	}
	queryWords := make([]string, 0, len(query))
	for word := range query {
		queryWords = append(queryWords, word)
	}
	sort.Strings(queryWords)
	df := map[string]int{}
	counts := []map[string]int{}
	titles := []map[string]int{}
	lengths := []int{}
	total := 0
	for _, doc := range input.Documents {
		freq := words(doc.Title + " " + doc.Text)
		title := words(doc.Title)
		n := 0
		for word, count := range freq {
			n += count
			if query[word] {
				df[word]++
			}
		}
		counts = append(counts, freq)
		titles = append(titles, title)
		lengths = append(lengths, n)
		total += n
	}
	average := float64(total) / float64(len(input.Documents))
	if average == 0 {
		average = 1
	}
	result := []Ranked{}
	for i, doc := range input.Documents {
		bm := 0.0
		boost := 0.0
		matched := []string{}
		for _, word := range queryWords {
			tf := float64(counts[i][word])
			if tf == 0 {
				continue
			}
			matched = append(matched, word)
			idf := math.Log(1 + (float64(len(input.Documents)-df[word])+0.5)/(float64(df[word])+0.5))
			bm += idf * (tf * 2.2) / (tf + 1.2*(0.25+0.75*float64(lengths[i])/average))
			if titles[i][word] > 0 {
				boost += 0.4 * idf
			}
		}
		minimum := 2
		if len(query) < 2 {
			minimum = len(query)
		}
		if len(matched) == 0 || len(matched) < minimum {
			continue
		}
		sort.Strings(matched)
		feedback := input.Feedback[doc.ID]
		if feedback > 1 {
			feedback = 1
		}
		if feedback < -1 {
			feedback = -1
		}
		adjustment := 0.25 * float64(feedback)
		result = append(result, Ranked{doc.ID, bm + boost + adjustment, bm, boost, adjustment, matched})
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].Score == result[j].Score {
			return result[i].ID < result[j].ID
		}
		return result[i].Score > result[j].Score
	})
	return result, nil
}

func main() {
	raw, err := io.ReadAll(io.LimitReader(os.Stdin, 65537))
	var request Request
	if err == nil && len(raw) > 65536 {
		err = fmt.Errorf("WORKER_INPUT_LIMIT")
	}
	if err == nil {
		decoder := json.NewDecoder(bytes.NewReader(raw))
		decoder.DisallowUnknownFields()
		err = decoder.Decode(&request)
		if err == nil {
			var extra any
			if decoder.Decode(&extra) != io.EOF {
				err = fmt.Errorf("TRAILING_DATA")
			}
		}
	}
	var output any
	if err == nil {
		output, err = execute(request)
	}
	response := map[string]any{"schema": "worker-response/1", "id": request.ID, "tool": request.Tool, "result": output, "error": nil, "external_effects": false}
	if err != nil {
		response["error"] = err.Error()
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetEscapeHTML(false)
	_ = encoder.Encode(response)
	if err != nil {
		os.Exit(2)
	}
}
