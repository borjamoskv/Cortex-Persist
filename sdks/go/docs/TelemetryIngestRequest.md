# TelemetryIngestRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Timestamp** | **int32** |  | 
**AgentId** | **string** |  | 
**Payload** | [**TelemetryPayload**](TelemetryPayload.md) |  | 
**LogosSignature** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewTelemetryIngestRequest

`func NewTelemetryIngestRequest(timestamp int32, agentId string, payload TelemetryPayload, ) *TelemetryIngestRequest`

NewTelemetryIngestRequest instantiates a new TelemetryIngestRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTelemetryIngestRequestWithDefaults

`func NewTelemetryIngestRequestWithDefaults() *TelemetryIngestRequest`

NewTelemetryIngestRequestWithDefaults instantiates a new TelemetryIngestRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTimestamp

`func (o *TelemetryIngestRequest) GetTimestamp() int32`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *TelemetryIngestRequest) GetTimestampOk() (*int32, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *TelemetryIngestRequest) SetTimestamp(v int32)`

SetTimestamp sets Timestamp field to given value.


### GetAgentId

`func (o *TelemetryIngestRequest) GetAgentId() string`

GetAgentId returns the AgentId field if non-nil, zero value otherwise.

### GetAgentIdOk

`func (o *TelemetryIngestRequest) GetAgentIdOk() (*string, bool)`

GetAgentIdOk returns a tuple with the AgentId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgentId

`func (o *TelemetryIngestRequest) SetAgentId(v string)`

SetAgentId sets AgentId field to given value.


### GetPayload

`func (o *TelemetryIngestRequest) GetPayload() TelemetryPayload`

GetPayload returns the Payload field if non-nil, zero value otherwise.

### GetPayloadOk

`func (o *TelemetryIngestRequest) GetPayloadOk() (*TelemetryPayload, bool)`

GetPayloadOk returns a tuple with the Payload field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPayload

`func (o *TelemetryIngestRequest) SetPayload(v TelemetryPayload)`

SetPayload sets Payload field to given value.


### GetLogosSignature

`func (o *TelemetryIngestRequest) GetLogosSignature() string`

GetLogosSignature returns the LogosSignature field if non-nil, zero value otherwise.

### GetLogosSignatureOk

`func (o *TelemetryIngestRequest) GetLogosSignatureOk() (*string, bool)`

GetLogosSignatureOk returns a tuple with the LogosSignature field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLogosSignature

`func (o *TelemetryIngestRequest) SetLogosSignature(v string)`

SetLogosSignature sets LogosSignature field to given value.

### HasLogosSignature

`func (o *TelemetryIngestRequest) HasLogosSignature() bool`

HasLogosSignature returns a boolean if a field has been set.

### SetLogosSignatureNil

`func (o *TelemetryIngestRequest) SetLogosSignatureNil(b bool)`

 SetLogosSignatureNil sets the value for LogosSignature to be an explicit nil

### UnsetLogosSignature
`func (o *TelemetryIngestRequest) UnsetLogosSignature()`

UnsetLogosSignature ensures that no value is present for LogosSignature, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


