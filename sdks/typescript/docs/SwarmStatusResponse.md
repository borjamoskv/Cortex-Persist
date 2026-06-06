
# SwarmStatusResponse


## Properties

Name | Type
------------ | -------------
`activeWorktrees` | number
`totalWorktrees` | number
`agentPids` | Array&lt;number&gt;
`timestamp` | string

## Example

```typescript
import type { SwarmStatusResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "activeWorktrees": null,
  "totalWorktrees": null,
  "agentPids": null,
  "timestamp": null,
} satisfies SwarmStatusResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SwarmStatusResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


