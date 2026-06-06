
# AskResponse

RAG response with answer and sources.

## Properties

Name | Type
------------ | -------------
`answer` | string
`sources` | [Array&lt;AskSource&gt;](AskSource.md)
`model` | string
`provider` | string
`factsFound` | number

## Example

```typescript
import type { AskResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "answer": null,
  "sources": null,
  "model": null,
  "provider": null,
  "factsFound": null,
} satisfies AskResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AskResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


