# GovernanceApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createApiKeyV1AdminKeysPost**](GovernanceApi.md#createapikeyv1adminkeyspost) | **POST** /v1/admin/keys | Create Api Key |
| [**deepHealthCheckV1HealthDeepGet**](GovernanceApi.md#deephealthcheckv1healthdeepget) | **GET** /v1/health/deep | Deep Health Check |
| [**executeCredibilityStrikeV1AdminCredibilityStrikePost**](GovernanceApi.md#executecredibilitystrikev1admincredibilitystrikepost) | **POST** /v1/admin/credibility-strike | Execute Credibility Strike |
| [**exportProjectV1ProjectsProjectExportGet**](GovernanceApi.md#exportprojectv1projectsprojectexportget) | **GET** /v1/projects/{project}/export | Export Project |
| [**generateHandoffContextV1HandoffPost**](GovernanceApi.md#generatehandoffcontextv1handoffpost) | **POST** /v1/handoff | Generate Handoff Context |
| [**getSystemStatusV1StatusGet**](GovernanceApi.md#getsystemstatusv1statusget) | **GET** /v1/status | Get System Status |
| [**listApiKeysV1AdminKeysGet**](GovernanceApi.md#listapikeysv1adminkeysget) | **GET** /v1/admin/keys | List Api Keys |



## createApiKeyV1AdminKeysPost

> ApiKeyResponse createApiKeyV1AdminKeysPost(name, tenantId, authorization)

Create Api Key

Sovereign Key Provisioning.  First key is self-provisioned (bootstrap). Subsequent keys require \&#39;admin\&#39; permission.

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { CreateApiKeyV1AdminKeysPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string
    name: name_example,
    // string (optional)
    tenantId: tenantId_example,
    // string (optional)
    authorization: authorization_example,
  } satisfies CreateApiKeyV1AdminKeysPostRequest;

  try {
    const data = await api.createApiKeyV1AdminKeysPost(body);
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
| **name** | `string` |  | [Defaults to `undefined`] |
| **tenantId** | `string` |  | [Optional] [Defaults to `&#39;default&#39;`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**ApiKeyResponse**](ApiKeyResponse.md)

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


## deepHealthCheckV1HealthDeepGet

> DeepHealthResponse deepHealthCheckV1HealthDeepGet(authorization)

Deep Health Check

Deep Health Check - probes all CORTEX subsystems.  Returns 200 if all checks pass, 503 if any subsystem is degraded. Designed for Kubernetes liveness/readiness probes.

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { DeepHealthCheckV1HealthDeepGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies DeepHealthCheckV1HealthDeepGetRequest;

  try {
    const data = await api.deepHealthCheckV1HealthDeepGet(body);
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
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**DeepHealthResponse**](DeepHealthResponse.md)

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


## executeCredibilityStrikeV1AdminCredibilityStrikePost

> { [key: string]: any; } executeCredibilityStrikeV1AdminCredibilityStrikePost(project, ultrathink, authorization)

Execute Credibility Strike

Execute a JIT credibility strike for a project.  Computes exergy, constructs Merkle roots, signs the root, performs replay validation, and takes database snapshots.

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { ExecuteCredibilityStrikeV1AdminCredibilityStrikePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string
    project: project_example,
    // boolean (optional)
    ultrathink: true,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ExecuteCredibilityStrikeV1AdminCredibilityStrikePostRequest;

  try {
    const data = await api.executeCredibilityStrikeV1AdminCredibilityStrikePost(body);
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
| **ultrathink** | `boolean` |  | [Optional] [Defaults to `true`] |
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


## exportProjectV1ProjectsProjectExportGet

> ExportResponse exportProjectV1ProjectsProjectExportGet(project, path, format, authorization)

Export Project

Sovereign Export - dumps project memory to a secure JSON artifact.  Enforces path incarceration to prevent directory traversal.

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { ExportProjectV1ProjectsProjectExportGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string
    project: project_example,
    // string (optional)
    path: path_example,
    // string (optional)
    format: format_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ExportProjectV1ProjectsProjectExportGetRequest;

  try {
    const data = await api.exportProjectV1ProjectsProjectExportGet(body);
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
| **path** | `string` |  | [Optional] [Defaults to `undefined`] |
| **format** | `string` |  | [Optional] [Defaults to `&#39;json&#39;`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**ExportResponse**](ExportResponse.md)

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


## generateHandoffContextV1HandoffPost

> { [key: string]: any; } generateHandoffContextV1HandoffPost(authorization)

Generate Handoff Context

Manifest a session handoff artifact with hot context and recent episodes.  Used for transferring agentic state between platforms (macOS -&gt; Web).

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { GenerateHandoffContextV1HandoffPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GenerateHandoffContextV1HandoffPostRequest;

  try {
    const data = await api.generateHandoffContextV1HandoffPost(body);
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


## getSystemStatusV1StatusGet

> StatusResponse getSystemStatusV1StatusGet(authorization)

Get System Status

Expose engine diagnostics and memory health metrics.

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { GetSystemStatusV1StatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetSystemStatusV1StatusGetRequest;

  try {
    const data = await api.getSystemStatusV1StatusGet(body);
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
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**StatusResponse**](StatusResponse.md)

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


## listApiKeysV1AdminKeysGet

> Array&lt;ApiKeyListItem&gt; listApiKeysV1AdminKeysGet(authorization)

List Api Keys

Expose non-sensitive metadata for all provisioned keys.

### Example

```ts
import {
  Configuration,
  GovernanceApi,
} from '';
import type { ListApiKeysV1AdminKeysGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new GovernanceApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListApiKeysV1AdminKeysGetRequest;

  try {
    const data = await api.listApiKeysV1AdminKeysGet(body);
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
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;ApiKeyListItem&gt;**](ApiKeyListItem.md)

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

