
# OracleRequest

Request to trigger The Oracle audit on a target.

## Properties

Name | Type
------------ | -------------
`targetUrl` | string
`agentType` | string
`depth` | number

## Example

```typescript
import type { OracleRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "targetUrl": null,
  "agentType": null,
  "depth": null,
} satisfies OracleRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as OracleRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


