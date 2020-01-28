from app import db
from models import Plot, Measure, check_all_files, check_all_plots

if __name__ == "__main__":
    if True:
        for i in range(50):
            m = Measure(kind = "VNA", relative_path = "/some/thing_%d.h5"%i)
            db.session.add(m)
        db.session.commit()

        for i in range(20):
            p = Plot(kind = "single")
            p.associate_files(file_paths = "/some/thing_%d.h5"%i)
        db.session.commit()

        path_lst = []
        p = Plot(kind = "multi")
        for i in range(20):
            path_lst.append(
                "/some/thing_%d.h5"%(i+20)
            )
        p.associate_files(file_paths = path_lst)
        db.session.commit()

        for i in range(20):
            p = Plot(kind = "single")
            p.associate_files(file_paths = "/some/thing_%d.h5"%31)
        db.session.commit()

        for my_plot in Plot.query.all():
            print("\n")
            print(my_plot.id)
            print(my_plot.get_sources())

        for my_measure in Measure.query.all():
                print("\n")
                print(my_measure.id)
                path_list, kind_list = my_measure.get_plots()
                for i in range(len(path_list)):
                    print(path_list[i],kind_list[i] )
    #USRP_Delay_20200124_181021.h5
    check_all_files()
    check_all_plots()
