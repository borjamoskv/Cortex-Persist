
# LLMStatusResponse

LLM provider status. [LLM_STATUS]

## Properties

Name | Type
------------ | -------------
`available` | boolean
`provider` | string
`model` | string
`supportedProviders` | Array&lt;string&gt;
`providers` | Array&lt;{ [key: string]: any; } | null&gt;

## Example

```typescript
import type { LLMStatusResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "available": null,
  "provider": null,
  "model": null,
  "supportedProviders": null,
  "providers": null,
} satisfies LLMStatusResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as LLMStatusResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


