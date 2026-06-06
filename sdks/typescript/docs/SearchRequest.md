
# SearchRequest


## Properties

Name | Type
------------ | -------------
`query` | string
`k` | number
`project` | string
`asOf` | string
`factType` | string
`tags` | Array&lt;string&gt;
`graphDepth` | number
`includeGraph` | boolean

## Example

```typescript
import type { SearchRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "query": null,
  "k": null,
  "project": null,
  "asOf": null,
  "factType": null,
  "tags": null,
  "graphDepth": null,
  "includeGraph": null,
} satisfies SearchRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SearchRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


