
# ContextSignalModel


## Properties

Name | Type
------------ | -------------
`source` | string
`signalType` | string
`content` | string
`project` | string
`timestamp` | string
`weight` | number

## Example

```typescript
import type { ContextSignalModel } from ''

// TODO: Update the object below with actual values
const example = {
  "source": null,
  "signalType": null,
  "content": null,
  "project": null,
  "timestamp": null,
  "weight": null,
} satisfies ContextSignalModel

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ContextSignalModel
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


