# CategoriesResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Categories** | **map[string]int32** |  | 
**Total** | **int32** |  | 
**Lang** | **string** |  | 

## Methods

### NewCategoriesResponse

`func NewCategoriesResponse(categories map[string]int32, total int32, lang string, ) *CategoriesResponse`

NewCategoriesResponse instantiates a new CategoriesResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCategoriesResponseWithDefaults

`func NewCategoriesResponseWithDefaults() *CategoriesResponse`

NewCategoriesResponseWithDefaults instantiates a new CategoriesResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCategories

`func (o *CategoriesResponse) GetCategories() map[string]int32`

GetCategories returns the Categories field if non-nil, zero value otherwise.

### GetCategoriesOk

`func (o *CategoriesResponse) GetCategoriesOk() (*map[string]int32, bool)`

GetCategoriesOk returns a tuple with the Categories field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCategories

`func (o *CategoriesResponse) SetCategories(v map[string]int32)`

SetCategories sets Categories field to given value.


### GetTotal

`func (o *CategoriesResponse) GetTotal() int32`

GetTotal returns the Total field if non-nil, zero value otherwise.

### GetTotalOk

`func (o *CategoriesResponse) GetTotalOk() (*int32, bool)`

GetTotalOk returns a tuple with the Total field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotal

`func (o *CategoriesResponse) SetTotal(v int32)`

SetTotal sets Total field to given value.


### GetLang

`func (o *CategoriesResponse) GetLang() string`

GetLang returns the Lang field if non-nil, zero value otherwise.

### GetLangOk

`func (o *CategoriesResponse) GetLangOk() (*string, bool)`

GetLangOk returns a tuple with the Lang field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLang

`func (o *CategoriesResponse) SetLang(v string)`

SetLang sets Lang field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


