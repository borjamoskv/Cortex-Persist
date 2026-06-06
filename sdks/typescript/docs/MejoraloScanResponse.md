
# MejoraloScanResponse


## Properties

Name | Type
------------ | -------------
`project` | string
`score` | number
`stack` | string
`dimensions` | [Array&lt;DimensionResultModel&gt;](DimensionResultModel.md)
`deadCode` | boolean
`totalFiles` | number
`totalLoc` | number
`factId` | number

## Example

```typescript
import type { MejoraloScanResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "project": null,
  "score": null,
  "stack": null,
  "dimensions": null,
  "deadCode": null,
  "totalFiles": null,
  "totalLoc": null,
  "factId": null,
} satisfies MejoraloScanResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MejoraloScanResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


