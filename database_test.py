from app import db
from models import Plot, Measure, check_all_files, check_all_plots, add_measure_entry, add_plot_entry

if __name__ == "__main__":
    if True:
        for i in range(50):
            add_measure_entry(relative_path = "/some/thing_%d.h5"%i, started_time = "some time", kind = "Unknown", comment = "", commit = True)

        for i in range(20):
            add_plot_entry(relative_path = "/some/thing_%d.png"%i, kind ="single", backend = "matplotlib", sources = "/some/thing_%d.h5"%i, comment = "", commit = True)

        path_lst = []
        for i in range(20):
            path_lst.append(
                "/some/thing_%d.h5"%i
            )
        add_plot_entry(relative_path = "/some/thing_multi.png", kind =  "multi", backend = "plotly", sources = path_lst, comment = "", commit = True)

        for i in range(20):
            add_plot_entry(relative_path = "/some/thing_%d.png"%(i+50), kind = "single", backend = "matplotly", sources = "/some/thing_%d.h5"%31, comment = "", commit = True)

        print("Printing stuff...")
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

    print("check twice")

    check_all_files()
    check_all_plots()
