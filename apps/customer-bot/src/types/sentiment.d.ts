declare module 'sentiment' {
  interface SentimentResult {
    score: number;
    comparative: number;
    tokens: string[];
    words: string[];
    positive: string[];
    negative: string[];
  }

  class Sentiment {
    constructor(options?: unknown);
    analyze(phrase: string, opts?: unknown, callback?: unknown): SentimentResult;
  }

  export default Sentiment;
}
