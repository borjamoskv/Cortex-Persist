# PsychohistoryRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ScenarioName** | **string** | The catastrophic scenario to simulate | 
**SimulatedYears** | Pointer to **int32** | Number of years to simulate into the future | [optional] [default to 5]
**Project** | Pointer to **string** | Project namespace to save the crystal | [optional] [default to "SYSTEM"]
**MaxConcurrency** | Pointer to **int32** | Maximum concurrency for LLM calls | [optional] [default to 5]

## Methods

### NewPsychohistoryRequest

`func NewPsychohistoryRequest(scenarioName string, ) *PsychohistoryRequest`

NewPsychohistoryRequest instantiates a new PsychohistoryRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewPsychohistoryRequestWithDefaults

`func NewPsychohistoryRequestWithDefaults() *PsychohistoryRequest`

NewPsychohistoryRequestWithDefaults instantiates a new PsychohistoryRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetScenarioName

`func (o *PsychohistoryRequest) GetScenarioName() string`

GetScenarioName returns the ScenarioName field if non-nil, zero value otherwise.

### GetScenarioNameOk

`func (o *PsychohistoryRequest) GetScenarioNameOk() (*string, bool)`

GetScenarioNameOk returns a tuple with the ScenarioName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScenarioName

`func (o *PsychohistoryRequest) SetScenarioName(v string)`

SetScenarioName sets ScenarioName field to given value.


### GetSimulatedYears

`func (o *PsychohistoryRequest) GetSimulatedYears() int32`

GetSimulatedYears returns the SimulatedYears field if non-nil, zero value otherwise.

### GetSimulatedYearsOk

`func (o *PsychohistoryRequest) GetSimulatedYearsOk() (*int32, bool)`

GetSimulatedYearsOk returns a tuple with the SimulatedYears field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSimulatedYears

`func (o *PsychohistoryRequest) SetSimulatedYears(v int32)`

SetSimulatedYears sets SimulatedYears field to given value.

### HasSimulatedYears

`func (o *PsychohistoryRequest) HasSimulatedYears() bool`

HasSimulatedYears returns a boolean if a field has been set.

### GetProject

`func (o *PsychohistoryRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *PsychohistoryRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *PsychohistoryRequest) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *PsychohistoryRequest) HasProject() bool`

HasProject returns a boolean if a field has been set.

### GetMaxConcurrency

`func (o *PsychohistoryRequest) GetMaxConcurrency() int32`

GetMaxConcurrency returns the MaxConcurrency field if non-nil, zero value otherwise.

### GetMaxConcurrencyOk

`func (o *PsychohistoryRequest) GetMaxConcurrencyOk() (*int32, bool)`

GetMaxConcurrencyOk returns a tuple with the MaxConcurrency field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMaxConcurrency

`func (o *PsychohistoryRequest) SetMaxConcurrency(v int32)`

SetMaxConcurrency sets MaxConcurrency field to given value.

### HasMaxConcurrency

`func (o *PsychohistoryRequest) HasMaxConcurrency() bool`

HasMaxConcurrency returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


