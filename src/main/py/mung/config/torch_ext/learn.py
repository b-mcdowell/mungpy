from mung.torch_ext.learn import Trainer

# Expects config of the form:
# {
#   max_evaluation : [INICATES WHETHER TO MAXIMIZE OVER EVALUATIONS (OR MINIMIZE)]
#   data : [NAME OF DATA SUBSET TO TRAIN ON]
#   (Optional) data_size : [SIZE OF DATA SUBSET TO TRAIN ON]
#   iterations : [TRAINING ITERATIONS]
#   batch_size : [BATCH SIZE]
#   optimizer_type : [OPTIMIZER TYPE]
#   learning_rate : [LEARNING RATE]
#   weight_decay : [WEIGHT DECAY]
#   gradient_clipping : [GRADIENT CLIPPING]
#   log_interval : [LOG INTERVAL]
# }
def train_from_config(config, data_parameter, loss_criterion, logger, evaluations, model, data_sets, best_part_fn=None):
    data = data_sets[config["data"]]
    if "data_size" in config:
        data.shuffle()
        data.get_subset(0, int(config["data_size"]))

    trainer = Trainer(data_parameter, loss_criterion, logger, \
            evaluations[0], other_evaluations=evaluations[1:len(evaluations)], \
            max_evaluation=bool(int(config["max_evaluation"])))
    
    iterations = int(config["iterations"])
    batch_size = int(config["batch_size"])
    optimizer_type = config["optimizer_type"]
    learning_rate = float(config["learning_rate"])
    weight_decay = float(config["weight_decay"])
    gradient_clipping = float(config["gradient_clipping"])
    log_interval = int(config["log_interval"])
    best_model, best_part, best_iteration = trainer.train(model, data, iterations, \
            batch_size=batch_size, optimizer_type=optimizer_type, lr=learning_rate, weight_decay=weight_decay, \
            grad_clip=gradient_clipping, log_interval=log_interval, best_part_fn=best_part_fn)

    return best_model, best_part, best_iteration
