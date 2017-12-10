# -*- mode: ruby -*-
# vi: set ft=ruby :

numnodes = 2
vmmemory = 512

nodes = []

(1..numnodes).each do |n|
	nodes.push({:name => "node#{n}", :ip => "192.168.10.#{n+1}"})
end

File.open("./hosts", 'w') { |file|
	nodes.each do |n|
		file.write("#{n[:ip]} #{n[:name]} #{n[:name]}\n")
	end
}

Vagrant.configure("2") do |config|
	config.vm.provider "virtualbox" do |v|
		v.memory = vmmemory
	end

	nodes.each do |node|
		config.vm.define node[:name] do |n|
			n.vm.box = "ubuntu/xenial64"
			n.vm.hostname = node[:name]
			n.vm.network "private_network", ip: "#{node[:ip]}"
			n.vm.provision "shell", privileged: true, inline: <<-SHELL
				mkdir /etc/rabbitmq
				echo 'loopback_users = none' > /etc/rabbitmq/rabbitmq.conf
			SHELL
			n.vm.provision "shell", path: "./install-rabbitmq.sh"
			if File.file?("./hosts")
				n.vm.provision "file", source: "hosts", destination: "/tmp/hosts"
				n.vm.provision "shell", inline: "cat /tmp/hosts >> /etc/hosts",
					privileged: true
			end
		end
	end
end
