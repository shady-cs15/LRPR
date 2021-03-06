import theano.tensor as T
from theano import function as fn
import numpy as np

from conv_layer import conv_pool_layer
from deconv_layer import deconv_unpool_layer
from auto_encoder import hidden_layer

def pretrain_conv_autoencoder(layer_index, input, image_shape, kernel_shape, batch_size=5, poolsize=(2, 2), learning_rate=0.1, unpool=False, switch=None):

	x = T.tensor4('x')
	layer0 = x.reshape(image_shape)
	index = T.lscalar()
	rng = np.random.RandomState(23455)

	hidden_layer = conv_pool_layer(
		rng,
		input=layer0,
		image_shape=image_shape,
		filter_shape=kernel_shape,
		poolsize=(1, 1),
		zero_pad=True
	)

	kernel_shape2=(kernel_shape[1], kernel_shape[0], kernel_shape[2],kernel_shape[3])
	image_shape2=(image_shape[0], kernel_shape[0], image_shape[2], image_shape[3])

	W_ = hidden_layer.W.transpose(1, 0, 2, 3)
	
	output_layer = conv_pool_layer(
		rng,
		input=hidden_layer.output,
		image_shape=image_shape2,
		filter_shape=kernel_shape2,
		poolsize=(1, 1),
		zero_pad=True
	)

	cost = T.mean(T.sqr(output_layer.output-layer0))
	params = hidden_layer.params + output_layer.params
	grads = T.grad(cost, params)
	updates = [
		(param_i, param_i - learning_rate* grad_i)
		for param_i, grad_i in zip(params, grads)
	]

	pretrain_fn = fn([index], cost, updates=updates, givens={
			x:input[index*batch_size: (index+1)*batch_size]
		})

	print 'Pretraining at layer #%d ...' %layer_index
	epoch = 0
	n_epochs = 50
	n_batches = input.shape.eval()[0] /batch_size

	while (epoch < n_epochs):
		epoch+=1
		costs= []
		for mini_batch_index in range(n_batches):
			costs.append(pretrain_fn(mini_batch_index))
		print 'layer: %d, epoch: %d, cost: ' %(layer_index, epoch), np.mean(costs)

	if (unpool==True):
		return deconv_unpool_layer(rng, input, kernel_shape, input.shape.eval(), unpoolsize=poolsize, switch=switch, read_file=True, W_input=hidden_layer.W, b_input=hidden_layer.b)
	return conv_pool_layer(rng, input, kernel_shape, input.shape.eval(), poolsize=poolsize, read_file=True, W_input=hidden_layer.W, b_input=hidden_layer.b), output_layer.params



def pretrain_local_autoencoders(layer_index, input, n_feature_maps, n_in, n_out, batch_size=5, learning_rate=0.1):
	x = T.tensor3('x')
	print input.shape.eval() #remove
	layer0 = T.reshape(x, (batch_size, n_feature_maps, n_in))
	index = T.lscalar()
	rng = np.random.RandomState(23455)

	encoding_layer = hidden_layer(
		rng,
		input=layer0,
		n_feature_maps=n_feature_maps,
		n_in=n_in,
		n_out=n_out
	)

	decoding_layer = hidden_layer(
		rng,
		input=encoding_layer.output,
		n_feature_maps=n_feature_maps,
		n_in=n_out,
		n_out=n_in
	)

	cost = T.mean(T.sqr(decoding_layer.output-layer0))
	params = encoding_layer.params + decoding_layer.params
	grads = T.grad(cost, params)
	updates = [
		(param_i, param_i - learning_rate * grad_i)
		for param_i, grad_i in zip(params, grads)
	]

	pretrain_fn = fn([index], cost, updates=updates, givens={
			x:input[index*batch_size: (index+1)*batch_size]
		})

	print 'Pretraining at layer #%d ...' %layer_index
	epoch = 0
	n_epochs = 100
	n_batches = input.shape.eval()[0] /batch_size

	while (epoch < n_epochs):
		epoch+=1
		costs= []
		for mini_batch_index in range(n_batches):
			costs.append(pretrain_fn(mini_batch_index))
		print 'layer: %d, epoch: %d, cost: ' %(layer_index, epoch), np.mean(costs)

	return hidden_layer(rng, input, n_feature_maps, n_in, n_out, read_file=True, W=encoding_layer.W, b=encoding_layer.b), decoding_layer.params
