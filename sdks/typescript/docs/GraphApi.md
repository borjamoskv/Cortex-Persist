# GraphApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getGraphAllV1GraphGet**](GraphApi.md#getgraphallv1graphget) | **GET** /v1/graph | Get Graph All |
| [**getGraphV1GraphProjectGet**](GraphApi.md#getgraphv1graphprojectget) | **GET** /v1/graph/{project} | Get Graph |



## getGraphAllV1GraphGet

> { [key: string]: any; } getGraphAllV1GraphGet(limit, authorization)

Get Graph All

Get entity graph across all projects.

### Example

```ts
import {
  Configuration,
  GraphApi,
} from '';
import type { GetGraphAllV1GraphGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GraphApi();

  const body = {
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetGraphAllV1GraphGetRequest;

  try {
    const data = await api.getGraphAllV1GraphGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **limit** | `number` |  | [Optional] [Defaults to `50`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGraphV1GraphProjectGet

> { [key: string]: any; } getGraphV1GraphProjectGet(project, limit, authorization)

Get Graph

Get entity graph for a specific project.

### Example

```ts
import {
  Configuration,
  GraphApi,
} from '';
import type { GetGraphV1GraphProjectGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GraphApi();

  const body = {
    // string
    project: project_example,
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetGraphV1GraphProjectGetRequest;

  try {
    const data = await api.getGraphV1GraphProjectGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **project** | `string` |  | [Defaults to `undefined`] |
| **limit** | `number` |  | [Optional] [Defaults to `50`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

