# TelemetryApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**addMafiaNodeApiV1TelemetryNodesPost**](TelemetryApi.md#addmafianodeapiv1telemetrynodespost) | **POST** /api/v1/telemetry/nodes | Add Mafia Node |
| [**addMafiaNodeTelemetryNodesPost**](TelemetryApi.md#addmafianodetelemetrynodespost) | **POST** /telemetry/nodes | Add Mafia Node |
| [**addMafiaNodeV1TelemetryNodesPost**](TelemetryApi.md#addmafianodev1telemetrynodespost) | **POST** /v1/telemetry/nodes | Add Mafia Node |
| [**getMafiaNodesApiV1TelemetryNodesGet**](TelemetryApi.md#getmafianodesapiv1telemetrynodesget) | **GET** /api/v1/telemetry/nodes | Get Mafia Nodes |
| [**getMafiaNodesTelemetryNodesGet**](TelemetryApi.md#getmafianodestelemetrynodesget) | **GET** /telemetry/nodes | Get Mafia Nodes |
| [**getMafiaNodesV1TelemetryNodesGet**](TelemetryApi.md#getmafianodesv1telemetrynodesget) | **GET** /v1/telemetry/nodes | Get Mafia Nodes |
| [**ingestTelemetryApiV1TelemetryIngestPost**](TelemetryApi.md#ingesttelemetryapiv1telemetryingestpost) | **POST** /api/v1/telemetry/ingest | Ingest Telemetry |
| [**ingestTelemetryTelemetryIngestPost**](TelemetryApi.md#ingesttelemetrytelemetryingestpost) | **POST** /telemetry/ingest | Ingest Telemetry |
| [**ingestTelemetryV1TelemetryIngestPost**](TelemetryApi.md#ingesttelemetryv1telemetryingestpost) | **POST** /v1/telemetry/ingest | Ingest Telemetry |



## addMafiaNodeApiV1TelemetryNodesPost

> any addMafiaNodeApiV1TelemetryNodesPost(mafiaNodeProposal)

Add Mafia Node

Add a new mafia node fact and push to all active extensions.

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { AddMafiaNodeApiV1TelemetryNodesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  const body = {
    // MafiaNodeProposal
    mafiaNodeProposal: ...,
  } satisfies AddMafiaNodeApiV1TelemetryNodesPostRequest;

  try {
    const data = await api.addMafiaNodeApiV1TelemetryNodesPost(body);
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
| **mafiaNodeProposal** | [MafiaNodeProposal](MafiaNodeProposal.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## addMafiaNodeTelemetryNodesPost

> any addMafiaNodeTelemetryNodesPost(mafiaNodeProposal)

Add Mafia Node

Add a new mafia node fact and push to all active extensions.

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { AddMafiaNodeTelemetryNodesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  const body = {
    // MafiaNodeProposal
    mafiaNodeProposal: ...,
  } satisfies AddMafiaNodeTelemetryNodesPostRequest;

  try {
    const data = await api.addMafiaNodeTelemetryNodesPost(body);
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
| **mafiaNodeProposal** | [MafiaNodeProposal](MafiaNodeProposal.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## addMafiaNodeV1TelemetryNodesPost

> any addMafiaNodeV1TelemetryNodesPost(mafiaNodeProposal)

Add Mafia Node

Add a new mafia node fact and push to all active extensions.

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { AddMafiaNodeV1TelemetryNodesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  const body = {
    // MafiaNodeProposal
    mafiaNodeProposal: ...,
  } satisfies AddMafiaNodeV1TelemetryNodesPostRequest;

  try {
    const data = await api.addMafiaNodeV1TelemetryNodesPost(body);
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
| **mafiaNodeProposal** | [MafiaNodeProposal](MafiaNodeProposal.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMafiaNodesApiV1TelemetryNodesGet

> any getMafiaNodesApiV1TelemetryNodesGet()

Get Mafia Nodes

Retrieve all active mafia nodes (base + dynamic).

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { GetMafiaNodesApiV1TelemetryNodesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  try {
    const data = await api.getMafiaNodesApiV1TelemetryNodesGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMafiaNodesTelemetryNodesGet

> any getMafiaNodesTelemetryNodesGet()

Get Mafia Nodes

Retrieve all active mafia nodes (base + dynamic).

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { GetMafiaNodesTelemetryNodesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  try {
    const data = await api.getMafiaNodesTelemetryNodesGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMafiaNodesV1TelemetryNodesGet

> any getMafiaNodesV1TelemetryNodesGet()

Get Mafia Nodes

Retrieve all active mafia nodes (base + dynamic).

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { GetMafiaNodesV1TelemetryNodesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  try {
    const data = await api.getMafiaNodesV1TelemetryNodesGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## ingestTelemetryApiV1TelemetryIngestPost

> any ingestTelemetryApiV1TelemetryIngestPost(telemetryIngestRequest)

Ingest Telemetry

Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { IngestTelemetryApiV1TelemetryIngestPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  const body = {
    // TelemetryIngestRequest
    telemetryIngestRequest: ...,
  } satisfies IngestTelemetryApiV1TelemetryIngestPostRequest;

  try {
    const data = await api.ingestTelemetryApiV1TelemetryIngestPost(body);
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
| **telemetryIngestRequest** | [TelemetryIngestRequest](TelemetryIngestRequest.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## ingestTelemetryTelemetryIngestPost

> any ingestTelemetryTelemetryIngestPost(telemetryIngestRequest)

Ingest Telemetry

Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { IngestTelemetryTelemetryIngestPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  const body = {
    // TelemetryIngestRequest
    telemetryIngestRequest: ...,
  } satisfies IngestTelemetryTelemetryIngestPostRequest;

  try {
    const data = await api.ingestTelemetryTelemetryIngestPost(body);
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
| **telemetryIngestRequest** | [TelemetryIngestRequest](TelemetryIngestRequest.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## ingestTelemetryV1TelemetryIngestPost

> any ingestTelemetryV1TelemetryIngestPost(telemetryIngestRequest)

Ingest Telemetry

Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.

### Example

```ts
import {
  Configuration,
  TelemetryApi,
} from '';
import type { IngestTelemetryV1TelemetryIngestPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TelemetryApi();

  const body = {
    // TelemetryIngestRequest
    telemetryIngestRequest: ...,
  } satisfies IngestTelemetryV1TelemetryIngestPostRequest;

  try {
    const data = await api.ingestTelemetryV1TelemetryIngestPost(body);
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
| **telemetryIngestRequest** | [TelemetryIngestRequest](TelemetryIngestRequest.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

