// TypeScript interfaces — must mirror api/models.py exactly.
//
// Field name drift between these interfaces and the Pydantic shapes is
// silent: the page renders nothing because the destructure fails.
// Use snake_case here for any field that is snake_case in the Pydantic
// model — do not camelCase.

export interface Entity {
  text: string;
  label: string;
  start: number;
  end: number;
}

export interface ExtractResponse {
  entities: Entity[];
}

export interface KGResponse {
  cypher: string;
  rows: Record<string, unknown>[];
  count: number;
}

export interface Citation {
  chunk_id: number;
  score: number;
}

export interface RAGResponse {
  answer: string;
  citations: Citation[];
  confidence: number;
}
