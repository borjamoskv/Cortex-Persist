# DeepHealthResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Status** | **string** |  | 
**Version** | **string** |  | 
**SchemaVersion** | **string** |  | 
**Checks** | [**map[string]HealthCheckDetail**](HealthCheckDetail.md) |  | 
**LatencyMs** | **float32** |  | 
**P95LatencyMs** | Pointer to **NullableFloat32** | p95 latency of ambient context boot | [optional] 
**StaleRatio** | Pointer to **NullableFloat32** | Ratio of facts older than 180 days with no hits | [optional] 

## Methods

### NewDeepHealthResponse

`func NewDeepHealthResponse(status string, version string, schemaVersion string, checks map[string]HealthCheckDetail, latencyMs float32, ) *DeepHealthResponse`

NewDeepHealthResponse instantiates a new DeepHealthResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeepHealthResponseWithDefaults

`func NewDeepHealthResponseWithDefaults() *DeepHealthResponse`

NewDeepHealthResponseWithDefaults instantiates a new DeepHealthResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStatus

`func (o *DeepHealthResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *DeepHealthResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *DeepHealthResponse) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetVersion

`func (o *DeepHealthResponse) GetVersion() string`

GetVersion returns the Version field if non-nil, zero value otherwise.

### GetVersionOk

`func (o *DeepHealthResponse) GetVersionOk() (*string, bool)`

GetVersionOk returns a tuple with the Version field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVersion

`func (o *DeepHealthResponse) SetVersion(v string)`

SetVersion sets Version field to given value.


### GetSchemaVersion

`func (o *DeepHealthResponse) GetSchemaVersion() string`

GetSchemaVersion returns the SchemaVersion field if non-nil, zero value otherwise.

### GetSchemaVersionOk

`func (o *DeepHealthResponse) GetSchemaVersionOk() (*string, bool)`

GetSchemaVersionOk returns a tuple with the SchemaVersion field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSchemaVersion

`func (o *DeepHealthResponse) SetSchemaVersion(v string)`

SetSchemaVersion sets SchemaVersion field to given value.


### GetChecks

`func (o *DeepHealthResponse) GetChecks() map[string]HealthCheckDetail`

GetChecks returns the Checks field if non-nil, zero value otherwise.

### GetChecksOk

`func (o *DeepHealthResponse) GetChecksOk() (*map[string]HealthCheckDetail, bool)`

GetChecksOk returns a tuple with the Checks field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetChecks

`func (o *DeepHealthResponse) SetChecks(v map[string]HealthCheckDetail)`

SetChecks sets Checks field to given value.


### GetLatencyMs

`func (o *DeepHealthResponse) GetLatencyMs() float32`

GetLatencyMs returns the LatencyMs field if non-nil, zero value otherwise.

### GetLatencyMsOk

`func (o *DeepHealthResponse) GetLatencyMsOk() (*float32, bool)`

GetLatencyMsOk returns a tuple with the LatencyMs field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLatencyMs

`func (o *DeepHealthResponse) SetLatencyMs(v float32)`

SetLatencyMs sets LatencyMs field to given value.


### GetP95LatencyMs

`func (o *DeepHealthResponse) GetP95LatencyMs() float32`

GetP95LatencyMs returns the P95LatencyMs field if non-nil, zero value otherwise.

### GetP95LatencyMsOk

`func (o *DeepHealthResponse) GetP95LatencyMsOk() (*float32, bool)`

GetP95LatencyMsOk returns a tuple with the P95LatencyMs field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetP95LatencyMs

`func (o *DeepHealthResponse) SetP95LatencyMs(v float32)`

SetP95LatencyMs sets P95LatencyMs field to given value.

### HasP95LatencyMs

`func (o *DeepHealthResponse) HasP95LatencyMs() bool`

HasP95LatencyMs returns a boolean if a field has been set.

### SetP95LatencyMsNil

`func (o *DeepHealthResponse) SetP95LatencyMsNil(b bool)`

 SetP95LatencyMsNil sets the value for P95LatencyMs to be an explicit nil

### UnsetP95LatencyMs
`func (o *DeepHealthResponse) UnsetP95LatencyMs()`

UnsetP95LatencyMs ensures that no value is present for P95LatencyMs, not even an explicit nil
### GetStaleRatio

`func (o *DeepHealthResponse) GetStaleRatio() float32`

GetStaleRatio returns the StaleRatio field if non-nil, zero value otherwise.

### GetStaleRatioOk

`func (o *DeepHealthResponse) GetStaleRatioOk() (*float32, bool)`

GetStaleRatioOk returns a tuple with the StaleRatio field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStaleRatio

`func (o *DeepHealthResponse) SetStaleRatio(v float32)`

SetStaleRatio sets StaleRatio field to given value.

### HasStaleRatio

`func (o *DeepHealthResponse) HasStaleRatio() bool`

HasStaleRatio returns a boolean if a field has been set.

### SetStaleRatioNil

`func (o *DeepHealthResponse) SetStaleRatioNil(b bool)`

 SetStaleRatioNil sets the value for StaleRatio to be an explicit nil

### UnsetStaleRatio
`func (o *DeepHealthResponse) UnsetStaleRatio()`

UnsetStaleRatio ensures that no value is present for StaleRatio, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


