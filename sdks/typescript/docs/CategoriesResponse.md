
# CategoriesResponse

Response for the categories endpoint.

## Properties

Name | Type
------------ | -------------
`categories` | { [key: string]: number; }
`total` | number
`lang` | string

## Example

```typescript
import type { CategoriesResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "categories": null,
  "total": null,
  "lang": null,
} satisfies CategoriesResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CategoriesResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


