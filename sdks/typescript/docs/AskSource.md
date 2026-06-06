
# AskSource

A source fact that contributed to the answer.

## Properties

Name | Type
------------ | -------------
`factId` | number
`content` | string
`score` | number
`project` | string

## Example

```typescript
import type { AskSource } from ''

// TODO: Update the object below with actual values
const example = {
  "factId": null,
  "content": null,
  "score": null,
  "project": null,
} satisfies AskSource

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AskSource
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


