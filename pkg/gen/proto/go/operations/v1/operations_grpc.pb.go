// Code generated by protoc-gen-go-grpc. DO NOT EDIT.
// versions:
// - protoc-gen-go-grpc v1.2.0
// - protoc             (unknown)
// source: operations/v1/operations.proto

package operationsv1

import (
	context "context"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
// Requires gRPC-Go v1.32.0 or later.
const _ = grpc.SupportPackageIsVersion7

// OperationsServiceClient is the client API for OperationsService service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type OperationsServiceClient interface {
	// CreateHypervisor creates and adds a new hypervisor on the pool
	CreateHypervisor(ctx context.Context, in *CreateHypervisorRequest, opts ...grpc.CallOption) (OperationsService_CreateHypervisorClient, error)
	// DestroyHypervisor destroys a Hypervisor. It doesn't stop / migrate the running VMs or anything like that
	DestroyHypervisor(ctx context.Context, in *DestroyHypervisorRequest, opts ...grpc.CallOption) (OperationsService_DestroyHypervisorClient, error)
	// ExpandStorage adds more storage to the shared storage pool
	ExpandStorage(ctx context.Context, in *ExpandStorageRequest, opts ...grpc.CallOption) (OperationsService_ExpandStorageClient, error)
	// ShrinkStorage removes storage from the shared storage pool
	ShrinkStorage(ctx context.Context, in *ShrinkStorageRequest, opts ...grpc.CallOption) (OperationsService_ShrinkStorageClient, error)
	// CreateBackup creates a new backup of the storage pool
	CreateBackup(ctx context.Context, in *CreateBackupRequest, opts ...grpc.CallOption) (OperationsService_CreateBackupClient, error)
}

type operationsServiceClient struct {
	cc grpc.ClientConnInterface
}

func NewOperationsServiceClient(cc grpc.ClientConnInterface) OperationsServiceClient {
	return &operationsServiceClient{cc}
}

func (c *operationsServiceClient) CreateHypervisor(ctx context.Context, in *CreateHypervisorRequest, opts ...grpc.CallOption) (OperationsService_CreateHypervisorClient, error) {
	stream, err := c.cc.NewStream(ctx, &OperationsService_ServiceDesc.Streams[0], "/operations.v1.OperationsService/CreateHypervisor", opts...)
	if err != nil {
		return nil, err
	}
	x := &operationsServiceCreateHypervisorClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type OperationsService_CreateHypervisorClient interface {
	Recv() (*CreateHypervisorResponse, error)
	grpc.ClientStream
}

type operationsServiceCreateHypervisorClient struct {
	grpc.ClientStream
}

func (x *operationsServiceCreateHypervisorClient) Recv() (*CreateHypervisorResponse, error) {
	m := new(CreateHypervisorResponse)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *operationsServiceClient) DestroyHypervisor(ctx context.Context, in *DestroyHypervisorRequest, opts ...grpc.CallOption) (OperationsService_DestroyHypervisorClient, error) {
	stream, err := c.cc.NewStream(ctx, &OperationsService_ServiceDesc.Streams[1], "/operations.v1.OperationsService/DestroyHypervisor", opts...)
	if err != nil {
		return nil, err
	}
	x := &operationsServiceDestroyHypervisorClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type OperationsService_DestroyHypervisorClient interface {
	Recv() (*DestroyHypervisorResponse, error)
	grpc.ClientStream
}

type operationsServiceDestroyHypervisorClient struct {
	grpc.ClientStream
}

func (x *operationsServiceDestroyHypervisorClient) Recv() (*DestroyHypervisorResponse, error) {
	m := new(DestroyHypervisorResponse)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *operationsServiceClient) ExpandStorage(ctx context.Context, in *ExpandStorageRequest, opts ...grpc.CallOption) (OperationsService_ExpandStorageClient, error) {
	stream, err := c.cc.NewStream(ctx, &OperationsService_ServiceDesc.Streams[2], "/operations.v1.OperationsService/ExpandStorage", opts...)
	if err != nil {
		return nil, err
	}
	x := &operationsServiceExpandStorageClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type OperationsService_ExpandStorageClient interface {
	Recv() (*ExpandStorageResponse, error)
	grpc.ClientStream
}

type operationsServiceExpandStorageClient struct {
	grpc.ClientStream
}

func (x *operationsServiceExpandStorageClient) Recv() (*ExpandStorageResponse, error) {
	m := new(ExpandStorageResponse)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *operationsServiceClient) ShrinkStorage(ctx context.Context, in *ShrinkStorageRequest, opts ...grpc.CallOption) (OperationsService_ShrinkStorageClient, error) {
	stream, err := c.cc.NewStream(ctx, &OperationsService_ServiceDesc.Streams[3], "/operations.v1.OperationsService/ShrinkStorage", opts...)
	if err != nil {
		return nil, err
	}
	x := &operationsServiceShrinkStorageClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type OperationsService_ShrinkStorageClient interface {
	Recv() (*ShrinkStorageResponse, error)
	grpc.ClientStream
}

type operationsServiceShrinkStorageClient struct {
	grpc.ClientStream
}

func (x *operationsServiceShrinkStorageClient) Recv() (*ShrinkStorageResponse, error) {
	m := new(ShrinkStorageResponse)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *operationsServiceClient) CreateBackup(ctx context.Context, in *CreateBackupRequest, opts ...grpc.CallOption) (OperationsService_CreateBackupClient, error) {
	stream, err := c.cc.NewStream(ctx, &OperationsService_ServiceDesc.Streams[4], "/operations.v1.OperationsService/CreateBackup", opts...)
	if err != nil {
		return nil, err
	}
	x := &operationsServiceCreateBackupClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type OperationsService_CreateBackupClient interface {
	Recv() (*CreateBackupResponse, error)
	grpc.ClientStream
}

type operationsServiceCreateBackupClient struct {
	grpc.ClientStream
}

func (x *operationsServiceCreateBackupClient) Recv() (*CreateBackupResponse, error) {
	m := new(CreateBackupResponse)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

// OperationsServiceServer is the server API for OperationsService service.
// All implementations must embed UnimplementedOperationsServiceServer
// for forward compatibility
type OperationsServiceServer interface {
	// CreateHypervisor creates and adds a new hypervisor on the pool
	CreateHypervisor(*CreateHypervisorRequest, OperationsService_CreateHypervisorServer) error
	// DestroyHypervisor destroys a Hypervisor. It doesn't stop / migrate the running VMs or anything like that
	DestroyHypervisor(*DestroyHypervisorRequest, OperationsService_DestroyHypervisorServer) error
	// ExpandStorage adds more storage to the shared storage pool
	ExpandStorage(*ExpandStorageRequest, OperationsService_ExpandStorageServer) error
	// ShrinkStorage removes storage from the shared storage pool
	ShrinkStorage(*ShrinkStorageRequest, OperationsService_ShrinkStorageServer) error
	// CreateBackup creates a new backup of the storage pool
	CreateBackup(*CreateBackupRequest, OperationsService_CreateBackupServer) error
	mustEmbedUnimplementedOperationsServiceServer()
}

// UnimplementedOperationsServiceServer must be embedded to have forward compatible implementations.
type UnimplementedOperationsServiceServer struct {
}

func (UnimplementedOperationsServiceServer) CreateHypervisor(*CreateHypervisorRequest, OperationsService_CreateHypervisorServer) error {
	return status.Errorf(codes.Unimplemented, "method CreateHypervisor not implemented")
}
func (UnimplementedOperationsServiceServer) DestroyHypervisor(*DestroyHypervisorRequest, OperationsService_DestroyHypervisorServer) error {
	return status.Errorf(codes.Unimplemented, "method DestroyHypervisor not implemented")
}
func (UnimplementedOperationsServiceServer) ExpandStorage(*ExpandStorageRequest, OperationsService_ExpandStorageServer) error {
	return status.Errorf(codes.Unimplemented, "method ExpandStorage not implemented")
}
func (UnimplementedOperationsServiceServer) ShrinkStorage(*ShrinkStorageRequest, OperationsService_ShrinkStorageServer) error {
	return status.Errorf(codes.Unimplemented, "method ShrinkStorage not implemented")
}
func (UnimplementedOperationsServiceServer) CreateBackup(*CreateBackupRequest, OperationsService_CreateBackupServer) error {
	return status.Errorf(codes.Unimplemented, "method CreateBackup not implemented")
}
func (UnimplementedOperationsServiceServer) mustEmbedUnimplementedOperationsServiceServer() {}

// UnsafeOperationsServiceServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to OperationsServiceServer will
// result in compilation errors.
type UnsafeOperationsServiceServer interface {
	mustEmbedUnimplementedOperationsServiceServer()
}

func RegisterOperationsServiceServer(s grpc.ServiceRegistrar, srv OperationsServiceServer) {
	s.RegisterService(&OperationsService_ServiceDesc, srv)
}

func _OperationsService_CreateHypervisor_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(CreateHypervisorRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(OperationsServiceServer).CreateHypervisor(m, &operationsServiceCreateHypervisorServer{stream})
}

type OperationsService_CreateHypervisorServer interface {
	Send(*CreateHypervisorResponse) error
	grpc.ServerStream
}

type operationsServiceCreateHypervisorServer struct {
	grpc.ServerStream
}

func (x *operationsServiceCreateHypervisorServer) Send(m *CreateHypervisorResponse) error {
	return x.ServerStream.SendMsg(m)
}

func _OperationsService_DestroyHypervisor_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(DestroyHypervisorRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(OperationsServiceServer).DestroyHypervisor(m, &operationsServiceDestroyHypervisorServer{stream})
}

type OperationsService_DestroyHypervisorServer interface {
	Send(*DestroyHypervisorResponse) error
	grpc.ServerStream
}

type operationsServiceDestroyHypervisorServer struct {
	grpc.ServerStream
}

func (x *operationsServiceDestroyHypervisorServer) Send(m *DestroyHypervisorResponse) error {
	return x.ServerStream.SendMsg(m)
}

func _OperationsService_ExpandStorage_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(ExpandStorageRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(OperationsServiceServer).ExpandStorage(m, &operationsServiceExpandStorageServer{stream})
}

type OperationsService_ExpandStorageServer interface {
	Send(*ExpandStorageResponse) error
	grpc.ServerStream
}

type operationsServiceExpandStorageServer struct {
	grpc.ServerStream
}

func (x *operationsServiceExpandStorageServer) Send(m *ExpandStorageResponse) error {
	return x.ServerStream.SendMsg(m)
}

func _OperationsService_ShrinkStorage_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(ShrinkStorageRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(OperationsServiceServer).ShrinkStorage(m, &operationsServiceShrinkStorageServer{stream})
}

type OperationsService_ShrinkStorageServer interface {
	Send(*ShrinkStorageResponse) error
	grpc.ServerStream
}

type operationsServiceShrinkStorageServer struct {
	grpc.ServerStream
}

func (x *operationsServiceShrinkStorageServer) Send(m *ShrinkStorageResponse) error {
	return x.ServerStream.SendMsg(m)
}

func _OperationsService_CreateBackup_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(CreateBackupRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(OperationsServiceServer).CreateBackup(m, &operationsServiceCreateBackupServer{stream})
}

type OperationsService_CreateBackupServer interface {
	Send(*CreateBackupResponse) error
	grpc.ServerStream
}

type operationsServiceCreateBackupServer struct {
	grpc.ServerStream
}

func (x *operationsServiceCreateBackupServer) Send(m *CreateBackupResponse) error {
	return x.ServerStream.SendMsg(m)
}

// OperationsService_ServiceDesc is the grpc.ServiceDesc for OperationsService service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var OperationsService_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "operations.v1.OperationsService",
	HandlerType: (*OperationsServiceServer)(nil),
	Methods:     []grpc.MethodDesc{},
	Streams: []grpc.StreamDesc{
		{
			StreamName:    "CreateHypervisor",
			Handler:       _OperationsService_CreateHypervisor_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "DestroyHypervisor",
			Handler:       _OperationsService_DestroyHypervisor_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "ExpandStorage",
			Handler:       _OperationsService_ExpandStorage_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "ShrinkStorage",
			Handler:       _OperationsService_ShrinkStorage_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "CreateBackup",
			Handler:       _OperationsService_CreateBackup_Handler,
			ServerStreams: true,
		},
	},
	Metadata: "operations/v1/operations.proto",
}