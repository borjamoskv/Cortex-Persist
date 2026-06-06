
# GateStatusResponse


## Properties

Name | Type
------------ | -------------
`policy` | string
`timeoutSeconds` | number
`pending` | number
`approved` | number
`denied` | number
`expired` | number
`executed` | number
`totalAuditEntries` | number

## Example

```typescript
import type { GateStatusResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "policy": null,
  "timeoutSeconds": null,
  "pending": null,
  "approved": null,
  "denied": null,
  "expired": null,
  "executed": null,
  "totalAuditEntries": null,
} satisfies GateStatusResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GateStatusResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


