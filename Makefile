all: client499 serv499

client499:
	chmod u+x client499.py
	ln -s client499.py client499

serv499:
	chmod u+x serv499.py
	ln -s serv499.py serv499

clean:
	rm -f *.pyc
	rm -rf res.* testres.* deleteme.*
