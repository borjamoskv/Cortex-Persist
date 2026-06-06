
# TipsListResponse

Response for tip list endpoints.

## Properties

Name | Type
------------ | -------------
`tips` | [Array&lt;TipResponse&gt;](TipResponse.md)
`count` | number
`lang` | string
`category` | string
`project` | string
`totalAvailable` | number

## Example

```typescript
import type { TipsListResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "tips": null,
  "count": null,
  "lang": null,
  "category": null,
  "project": null,
  "totalAvailable": null,
} satisfies TipsListResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TipsListResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


