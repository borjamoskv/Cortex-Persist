
# TipResponse

Serialized tip for API responses.

## Properties

Name | Type
------------ | -------------
`id` | string
`content` | string
`category` | string
`lang` | string
`source` | string
`project` | string
`relevance` | number
`formatted` | string

## Example

```typescript
import type { TipResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "content": null,
  "category": null,
  "lang": null,
  "source": null,
  "project": null,
  "relevance": null,
  "formatted": null,
} satisfies TipResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TipResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


