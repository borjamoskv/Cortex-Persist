
# ApiKeyResponse

Response after creating an API key.

## Properties

Name | Type
------------ | -------------
`key` | string
`name` | string
`prefix` | string
`tenantId` | string
`message` | string

## Example

```typescript
import type { ApiKeyResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "key": null,
  "name": null,
  "prefix": null,
  "tenantId": null,
  "message": null,
} satisfies ApiKeyResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ApiKeyResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


