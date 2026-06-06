# TipsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getTipsByCategoryTipsCategoryCategoryGet**](TipsApi.md#gettipsbycategorytipscategorycategoryget) | **GET** /tips/category/{category} | Get Tips By Category |
| [**getTipsByProjectTipsProjectProjectGet**](TipsApi.md#gettipsbyprojecttipsprojectprojectget) | **GET** /tips/project/{project} | Get Tips By Project |
| [**getTipsTipsGet**](TipsApi.md#gettipstipsget) | **GET** /tips | Get Tips |
| [**listCategoriesTipsCategoriesGet**](TipsApi.md#listcategoriestipscategoriesget) | **GET** /tips/categories | List Categories |



## getTipsByCategoryTipsCategoryCategoryGet

> TipsListResponse getTipsByCategoryTipsCategoryCategoryGet(category, lang, limit, authorization)

Get Tips By Category

Get tips filtered by category.

### Example

```ts
import {
  Configuration,
  TipsApi,
} from '';
import type { GetTipsByCategoryTipsCategoryCategoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TipsApi();

  const body = {
    // string
    category: category_example,
    // string | Language code (en, es, eu) (optional)
    lang: lang_example,
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetTipsByCategoryTipsCategoryCategoryGetRequest;

  try {
    const data = await api.getTipsByCategoryTipsCategoryCategoryGet(body);
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
| **category** | `string` |  | [Defaults to `undefined`] |
| **lang** | `string` | Language code (en, es, eu) | [Optional] [Defaults to `&#39;en&#39;`] |
| **limit** | `number` |  | [Optional] [Defaults to `5`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TipsListResponse**](TipsListResponse.md)

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


## getTipsByProjectTipsProjectProjectGet

> TipsListResponse getTipsByProjectTipsProjectProjectGet(project, lang, limit, authorization)

Get Tips By Project

Get tips scoped to a specific project.

### Example

```ts
import {
  Configuration,
  TipsApi,
} from '';
import type { GetTipsByProjectTipsProjectProjectGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TipsApi();

  const body = {
    // string
    project: project_example,
    // string | Language code (en, es, eu) (optional)
    lang: lang_example,
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetTipsByProjectTipsProjectProjectGetRequest;

  try {
    const data = await api.getTipsByProjectTipsProjectProjectGet(body);
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
| **lang** | `string` | Language code (en, es, eu) | [Optional] [Defaults to `&#39;en&#39;`] |
| **limit** | `number` |  | [Optional] [Defaults to `3`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TipsListResponse**](TipsListResponse.md)

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


## getTipsTipsGet

> TipsListResponse getTipsTipsGet(count, lang, authorization)

Get Tips

Get random contextual tips.

### Example

```ts
import {
  Configuration,
  TipsApi,
} from '';
import type { GetTipsTipsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TipsApi();

  const body = {
    // number | Number of tips to return (optional)
    count: 56,
    // string | Language code (en, es, eu) (optional)
    lang: lang_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetTipsTipsGetRequest;

  try {
    const data = await api.getTipsTipsGet(body);
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
| **count** | `number` | Number of tips to return | [Optional] [Defaults to `1`] |
| **lang** | `string` | Language code (en, es, eu) | [Optional] [Defaults to `&#39;en&#39;`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TipsListResponse**](TipsListResponse.md)

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


## listCategoriesTipsCategoriesGet

> CategoriesResponse listCategoriesTipsCategoriesGet(lang, authorization)

List Categories

List all tip categories with counts.

### Example

```ts
import {
  Configuration,
  TipsApi,
} from '';
import type { ListCategoriesTipsCategoriesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TipsApi();

  const body = {
    // string | Language code (en, es, eu) (optional)
    lang: lang_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListCategoriesTipsCategoriesGetRequest;

  try {
    const data = await api.listCategoriesTipsCategoriesGet(body);
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
| **lang** | `string` | Language code (en, es, eu) | [Optional] [Defaults to `&#39;en&#39;`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**CategoriesResponse**](CategoriesResponse.md)

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

