
# ExportResponse

Response for project memory export.

## Properties

Name | Type
------------ | -------------
`status` | string
`project` | string
`artifact` | string
`message` | string

## Example

```typescript
import type { ExportResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "project": null,
  "artifact": null,
  "message": null,
} satisfies ExportResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ExportResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


