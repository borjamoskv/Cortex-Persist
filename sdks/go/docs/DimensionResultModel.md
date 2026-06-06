# DimensionResultModel

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** |  | 
**Score** | **int32** |  | 
**Weight** | **string** |  | 
**Findings** | Pointer to **[]string** |  | [optional] 

## Methods

### NewDimensionResultModel

`func NewDimensionResultModel(name string, score int32, weight string, ) *DimensionResultModel`

NewDimensionResultModel instantiates a new DimensionResultModel object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDimensionResultModelWithDefaults

`func NewDimensionResultModelWithDefaults() *DimensionResultModel`

NewDimensionResultModelWithDefaults instantiates a new DimensionResultModel object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *DimensionResultModel) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *DimensionResultModel) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *DimensionResultModel) SetName(v string)`

SetName sets Name field to given value.


### GetScore

`func (o *DimensionResultModel) GetScore() int32`

GetScore returns the Score field if non-nil, zero value otherwise.

### GetScoreOk

`func (o *DimensionResultModel) GetScoreOk() (*int32, bool)`

GetScoreOk returns a tuple with the Score field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScore

`func (o *DimensionResultModel) SetScore(v int32)`

SetScore sets Score field to given value.


### GetWeight

`func (o *DimensionResultModel) GetWeight() string`

GetWeight returns the Weight field if non-nil, zero value otherwise.

### GetWeightOk

`func (o *DimensionResultModel) GetWeightOk() (*string, bool)`

GetWeightOk returns a tuple with the Weight field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWeight

`func (o *DimensionResultModel) SetWeight(v string)`

SetWeight sets Weight field to given value.


### GetFindings

`func (o *DimensionResultModel) GetFindings() []string`

GetFindings returns the Findings field if non-nil, zero value otherwise.

### GetFindingsOk

`func (o *DimensionResultModel) GetFindingsOk() (*[]string, bool)`

GetFindingsOk returns a tuple with the Findings field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFindings

`func (o *DimensionResultModel) SetFindings(v []string)`

SetFindings sets Findings field to given value.

### HasFindings

`func (o *DimensionResultModel) HasFindings() bool`

HasFindings returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


