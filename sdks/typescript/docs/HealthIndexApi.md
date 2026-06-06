# HealthIndexApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**healthIndexCheckV1HealthCheckGet**](HealthIndexApi.md#healthindexcheckv1healthcheckget) | **GET** /v1/health/check | Health Index Check |
| [**healthIndexHistoryV1HealthHistoryGet**](HealthIndexApi.md#healthindexhistoryv1healthhistoryget) | **GET** /v1/health/history | Health Index History |
| [**healthIndexMetricsV1HealthMetricsGet**](HealthIndexApi.md#healthindexmetricsv1healthmetricsget) | **GET** /v1/health/metrics | Health Index Metrics |
| [**healthIndexPrometheusV1HealthPrometheusGet**](HealthIndexApi.md#healthindexprometheusv1healthprometheusget) | **GET** /v1/health/prometheus | Health Index Prometheus |
| [**healthIndexReportV1HealthReportGet**](HealthIndexApi.md#healthindexreportv1healthreportget) | **GET** /v1/health/report | Health Index Report |
| [**healthIndexScoreV1HealthScoreGet**](HealthIndexApi.md#healthindexscorev1healthscoreget) | **GET** /v1/health/score | Health Index Score |



## healthIndexCheckV1HealthCheckGet

> { [key: string]: any; } healthIndexCheckV1HealthCheckGet()

Health Index Check

Quick health check - score, grade, healthy boolean.

### Example

```ts
import {
  Configuration,
  HealthIndexApi,
} from '';
import type { HealthIndexCheckV1HealthCheckGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new HealthIndexApi();

  try {
    const data = await api.healthIndexCheckV1HealthCheckGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## healthIndexHistoryV1HealthHistoryGet

> { [key: string]: any; } healthIndexHistoryV1HealthHistoryGet(limit)

Health Index History

Persisted health score history.

### Example

```ts
import {
  Configuration,
  HealthIndexApi,
} from '';
import type { HealthIndexHistoryV1HealthHistoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new HealthIndexApi();

  const body = {
    // number (optional)
    limit: 56,
  } satisfies HealthIndexHistoryV1HealthHistoryGetRequest;

  try {
    const data = await api.healthIndexHistoryV1HealthHistoryGet(body);
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
| **limit** | `number` |  | [Optional] [Defaults to `20`] |

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


## healthIndexMetricsV1HealthMetricsGet

> { [key: string]: any; } healthIndexMetricsV1HealthMetricsGet()

Health Index Metrics

Raw metric snapshots for monitoring dashboards.

### Example

```ts
import {
  Configuration,
  HealthIndexApi,
} from '';
import type { HealthIndexMetricsV1HealthMetricsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new HealthIndexApi();

  try {
    const data = await api.healthIndexMetricsV1HealthMetricsGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## healthIndexPrometheusV1HealthPrometheusGet

> any healthIndexPrometheusV1HealthPrometheusGet()

Health Index Prometheus

Prometheus text exposition format.

### Example

```ts
import {
  Configuration,
  HealthIndexApi,
} from '';
import type { HealthIndexPrometheusV1HealthPrometheusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new HealthIndexApi();

  try {
    const data = await api.healthIndexPrometheusV1HealthPrometheusGet();
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


## healthIndexReportV1HealthReportGet

> { [key: string]: any; } healthIndexReportV1HealthReportGet()

Health Index Report

Full health report with recommendations and warnings.

### Example

```ts
import {
  Configuration,
  HealthIndexApi,
} from '';
import type { HealthIndexReportV1HealthReportGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new HealthIndexApi();

  try {
    const data = await api.healthIndexReportV1HealthReportGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## healthIndexScoreV1HealthScoreGet

> { [key: string]: any; } healthIndexScoreV1HealthScoreGet()

Health Index Score

Numeric score only (0-100).

### Example

```ts
import {
  Configuration,
  HealthIndexApi,
} from '';
import type { HealthIndexScoreV1HealthScoreGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new HealthIndexApi();

  try {
    const data = await api.healthIndexScoreV1HealthScoreGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

