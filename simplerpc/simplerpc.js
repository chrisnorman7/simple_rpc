class RPC {
    constructor(soc) {
        this.id = 0
        this.soc = soc
        soc.onmessage = event => this.receive(event)
        this.promises = {}
        this.commands = {}
        this.python = {}
    }
    send(name, args, kwargs, id) {
        let data = JSON.stringify([name, args, kwargs, id])
        this.soc.send(data)
    }
    receive(event) {
        let obj = JSON.parse(event.data)
        let name = obj.name
        let args = obj.args || []
        let kwargs = obj.kwargs || {}
        let id = obj.id
        this.handleCommand(name, args, kwargs, id)
    }
    call(name, args, kwargs) {
        this.id += 1
        if (args === undefined) {
            args = []
        }
        if (kwargs === undefined) {
            kwargs = {}
        }
        return new Promise((resolve, reject) => {
            this.promises[this.id] = {
                return: resolve,
                error: reject
            }
            this.send(name, args, kwargs, this.id)
        })
    }
    return(id, value) {
        let p = this.promises[id]
        if (p === undefined) {
            throw Error(`Return value provided for invalid ID: ${id}.`)
        } else {
            p.return(value)
        }
    }
    error(id, message) {
        let p = this.promises[id]
        if (p === undefined) {
            throw Error(`Error value provided for invalid ID: ${id}.`)
        } else {
            p.error(message)
        }
    }
    populateCommands(commands) {
        for (let i = 0; i < commands.length; i++) {
            /// Commands are sent in the format [name, args]. Here we ignore the args for now.
            let name = commands[i][0]
            this.python[name] = (...args) => this.call(name, args)
        }
    }
    handleCommand(name, args, kwargs, id) {
        if (["_return", "_error"].includes(name)) {
            let [id, value] = args
            this[name.slice(1, name.length)](id, value)
        } else if (name == "_commands") {
            this.populateCommands(args[0])
        } else if (name in this.commands) {
            let func = this.commands[name]
            try {
                let value = func(...args, kwargs)
                this.doReturn(id, value)
            }
            catch(err) {
                this.doError(id, err.message)
            }
        } else {
            throw Error(`Invalid command: ${name}.`)
        }
    }
}

window.RPC = RPC
