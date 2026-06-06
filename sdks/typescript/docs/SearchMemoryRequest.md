
# SearchMemoryRequest


## Properties

Name | Type
------------ | -------------
`query` | string
`k` | number
`project` | string
`tags` | Array&lt;string&gt;
`asOf` | string

## Example

```typescript
import type { SearchMemoryRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "query": null,
  "k": null,
  "project": null,
  "tags": null,
  "asOf": null,
} satisfies SearchMemoryRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SearchMemoryRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


