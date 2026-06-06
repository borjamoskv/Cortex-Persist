
# MejoraloShipResponse


## Properties

Name | Type
------------ | -------------
`project` | string
`ready` | boolean
`seals` | [Array&lt;ShipSealModel&gt;](ShipSealModel.md)
`passed` | number
`total` | number

## Example

```typescript
import type { MejoraloShipResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "project": null,
  "ready": null,
  "seals": null,
  "passed": null,
  "total": null,
} satisfies MejoraloShipResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MejoraloShipResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


